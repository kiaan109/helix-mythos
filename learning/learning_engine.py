"""
Helix Mythos — Learning Engine
Multi-model ensemble · Knowledge graph · Topic modeling · Clustering ·
Anomaly detection · Trend tracking · Auto-summarization · Reinforcement
"""

import re
import time
import pickle
import logging
import threading
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger("HelixLearning")

MODEL_PATH = Path("helix_learning_model.pkl")

# ── sklearn imports ───────────────────────────────────────────────────────────
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.linear_model import SGDClassifier
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.decomposition import NMF
    from sklearn.cluster import KMeans
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import normalize
    import numpy as np
    SKLEARN_AVAILABLE = True
    logger.info("scikit-learn available.")
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed. Learning engine will use basic mode.")

# ── networkx knowledge graph ──────────────────────────────────────────────────
try:
    import networkx as nx
    NX_AVAILABLE = True
    logger.info("networkx available.")
except ImportError:
    NX_AVAILABLE = False
    logger.warning("networkx not installed. Knowledge graph disabled.")

# ── scipy ─────────────────────────────────────────────────────────────────────
try:
    from scipy.sparse import issparse
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class LearningEngine:
    def __init__(self, memory=None):
        self.memory          = memory
        self._running        = False
        self._thread         = None
        self._lock           = threading.Lock()

        # Training corpus
        self._texts          = []   # list of str
        self._labels         = []   # list of str (category)
        self._timestamps     = []   # list of float

        # Ensemble models (TF-IDF + classifier pipelines)
        self._pipe_nb        = None
        self._pipe_sgd       = None
        self._pipe_rf        = None
        self._tfidf_raw      = None   # standalone vectorizer for NMF / IsolationForest

        # Knowledge graph
        self._graph          = nx.DiGraph() if NX_AVAILABLE else None

        # NMF topic model
        self._nmf_model      = None
        self._nmf_tfidf      = None
        self._nmf_components = 10

        # KMeans clustering
        self._kmeans         = None
        self._n_clusters     = 8

        # IsolationForest anomaly detection
        self._iso_forest     = None

        # Confidence scores per label
        self._confidence     = defaultdict(lambda: 0.5)

        # Trend tracking: keyword -> Counter per day bucket
        self._trend_data     = defaultdict(Counter)  # word -> {date_str: count}

        # Named entities store
        self._entities       = defaultdict(set)   # type -> set of values

        # Summary cache
        self._summary_cache  = ""
        self._report_cache   = {}

        # Internal counters
        self._train_count    = 0
        self._predictions    = 0
        self._correct        = 0

        self._load_state()
        logger.info(f"LearningEngine initialized. Corpus size: {len(self._texts)}")

    # ── Start / stop ──────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._retrain_loop, daemon=True, name="Learning"
        )
        self._thread.start()
        logger.info(f"Learning Engine started — retraining every {config.LEARNING_INTERVAL}s.")

    def stop(self):
        self._running = False

    # ── Public ingest API ─────────────────────────────────────────────────────
    def ingest(self, text, label="general", ts=None):
        """Add a new text sample to the corpus and update knowledge graph."""
        if not text or not isinstance(text, str):
            return
        text = text.strip()[:2000]
        with self._lock:
            self._texts.append(text)
            self._labels.append(label)
            self._timestamps.append(ts or time.time())
            self._update_graph(text, label)
            self._extract_entities(text)
            self._update_trends(text)

    def predict(self, text):
        """Predict category for text using ensemble vote."""
        if not SKLEARN_AVAILABLE or not text:
            return "unknown", 0.0
        with self._lock:
            votes    = []
            conf_sum = 0.0
            for pipe in [self._pipe_nb, self._pipe_sgd, self._pipe_rf]:
                if pipe is None:
                    continue
                try:
                    pred = pipe.predict([text])[0]
                    votes.append(pred)
                    if hasattr(pipe, "predict_proba"):
                        proba = pipe.predict_proba([text])
                        conf_sum += float(proba.max())
                except Exception:
                    pass
            if not votes:
                return "unknown", 0.0
            winner  = Counter(votes).most_common(1)[0][0]
            avg_conf = conf_sum / len(votes) if votes else 0.0
            self._predictions += 1
            return winner, round(avg_conf, 3)

    def reinforce(self, text, predicted, actual):
        """Reinforce learning: adjust confidence score."""
        with self._lock:
            if predicted == actual:
                self._correct      += 1
                self._confidence[actual] = min(
                    1.0, self._confidence[actual] + 0.02
                )
            else:
                self._confidence[predicted] = max(
                    0.0, self._confidence[predicted] - 0.05
                )

    # ── Retrain loop ──────────────────────────────────────────────────────────
    def _retrain_loop(self):
        while self._running:
            try:
                self._train_all()
                self._save_state()
            except Exception as e:
                logger.error(f"Retrain error: {e}")
            time.sleep(config.LEARNING_INTERVAL)

    def _train_all(self):
        with self._lock:
            texts  = list(self._texts)
            labels = list(self._labels)

        if len(texts) < 5:
            logger.info("Corpus too small to train — need at least 5 samples.")
            return

        self._train_count += 1
        logger.info(
            f"Training cycle #{self._train_count} — {len(texts)} samples, "
            f"{len(set(labels))} categories."
        )

        if not SKLEARN_AVAILABLE:
            return

        # ── Ensemble pipelines ────────────────────────────────────────────
        try:
            self._pipe_nb = Pipeline([
                ("tfidf", TfidfVectorizer(
                    max_features=8000, ngram_range=(1, 2), sublinear_tf=True
                )),
                ("clf", MultinomialNB(alpha=0.5)),
            ])
            self._pipe_nb.fit(texts, labels)
        except Exception as e:
            logger.debug(f"NB pipeline error: {e}")
            self._pipe_nb = None

        try:
            self._pipe_sgd = Pipeline([
                ("tfidf", TfidfVectorizer(
                    max_features=8000, ngram_range=(1, 2), sublinear_tf=True
                )),
                ("clf", SGDClassifier(
                    loss="hinge", max_iter=1000, tol=1e-3,
                    random_state=42, n_jobs=-1
                )),
            ])
            self._pipe_sgd.fit(texts, labels)
        except Exception as e:
            logger.debug(f"SGD pipeline error: {e}")
            self._pipe_sgd = None

        try:
            self._pipe_rf = Pipeline([
                ("tfidf", TfidfVectorizer(
                    max_features=5000, ngram_range=(1, 1), sublinear_tf=True
                )),
                ("clf", RandomForestClassifier(
                    n_estimators=80, max_depth=12,
                    random_state=42, n_jobs=-1
                )),
            ])
            self._pipe_rf.fit(texts, labels)
        except Exception as e:
            logger.debug(f"RF pipeline error: {e}")
            self._pipe_rf = None

        # ── Shared TF-IDF for NMF / IsolationForest / KMeans ─────────────
        try:
            self._tfidf_raw = TfidfVectorizer(
                max_features=6000, ngram_range=(1, 2),
                sublinear_tf=True, min_df=2
            )
            X = self._tfidf_raw.fit_transform(texts)
        except Exception as e:
            logger.debug(f"TF-IDF error: {e}")
            X = None

        if X is not None:
            self._train_nmf(X)
            self._train_kmeans(X)
            self._train_isolation_forest(X)

        accuracy = self._correct / max(self._predictions, 1)
        logger.info(
            f"Training #{self._train_count} done. "
            f"Accuracy: {accuracy*100:.1f}%  "
            f"Confidence map: {dict(list(self._confidence.items())[:5])}"
        )
        self._build_report(texts, labels)

    # ── NMF Topic Modeling ────────────────────────────────────────────────────
    def _train_nmf(self, X):
        try:
            n_topics = min(self._nmf_components, X.shape[0] - 1, 20)
            if n_topics < 2:
                return
            self._nmf_model = NMF(
                n_components=n_topics, max_iter=300,
                random_state=42, init="nndsvda"
            )
            self._nmf_model.fit(X)
            self._nmf_tfidf = self._tfidf_raw
            logger.info(f"NMF: {n_topics} topics extracted.")
        except Exception as e:
            logger.debug(f"NMF error: {e}")

    def get_topics(self, n_top_words=8):
        """Return top words per NMF topic."""
        topics = []
        if self._nmf_model is None or self._nmf_tfidf is None:
            return topics
        try:
            feature_names = self._nmf_tfidf.get_feature_names_out()
            for topic_idx, topic in enumerate(self._nmf_model.components_):
                top_words = [
                    feature_names[i]
                    for i in topic.argsort()[:-n_top_words - 1:-1]
                ]
                topics.append({
                    "topic_id": topic_idx,
                    "words":    top_words,
                    "weight":   float(topic.sum()),
                })
        except Exception as e:
            logger.debug(f"get_topics error: {e}")
        return topics

    # ── KMeans Clustering ─────────────────────────────────────────────────────
    def _train_kmeans(self, X):
        try:
            n_clust = min(self._n_clusters, X.shape[0] - 1)
            if n_clust < 2:
                return
            self._kmeans = KMeans(
                n_clusters=n_clust, random_state=42,
                n_init=10, max_iter=300
            )
            self._kmeans.fit(X)
            logger.info(f"KMeans: {n_clust} clusters found.")
        except Exception as e:
            logger.debug(f"KMeans error: {e}")

    def get_clusters(self):
        """Return cluster label counts."""
        if self._kmeans is None:
            return {}
        try:
            labels = self._kmeans.labels_
            return dict(Counter(int(l) for l in labels))
        except Exception:
            return {}

    def get_cluster_for_text(self, text):
        """Return cluster ID for a given text."""
        if self._kmeans is None or self._tfidf_raw is None:
            return -1
        try:
            vec = self._tfidf_raw.transform([text])
            return int(self._kmeans.predict(vec)[0])
        except Exception:
            return -1

    # ── IsolationForest Anomaly Detection ─────────────────────────────────────
    def _train_isolation_forest(self, X):
        try:
            if X.shape[0] < 10:
                return
            if issparse(X) if SCIPY_AVAILABLE else False:
                X_dense = X.toarray()
            else:
                X_dense = X.toarray() if hasattr(X, "toarray") else X
            self._iso_forest = IsolationForest(
                contamination=0.05, random_state=42, n_estimators=100
            )
            self._iso_forest.fit(X_dense)
            logger.info("IsolationForest trained.")
        except Exception as e:
            logger.debug(f"IsolationForest error: {e}")

    def is_anomaly(self, text):
        """Return True if text is an anomalous event."""
        if self._iso_forest is None or self._tfidf_raw is None:
            return False
        try:
            vec   = self._tfidf_raw.transform([text])
            dense = vec.toarray() if hasattr(vec, "toarray") else vec
            pred  = self._iso_forest.predict(dense)
            return int(pred[0]) == -1
        except Exception:
            return False

    def get_anomalies(self, limit=10):
        """Return texts flagged as anomalies from the corpus."""
        anomalies = []
        if self._iso_forest is None or self._tfidf_raw is None:
            return anomalies
        with self._lock:
            texts = list(self._texts[-200:])  # check last 200
        try:
            vec    = self._tfidf_raw.transform(texts)
            dense  = vec.toarray() if hasattr(vec, "toarray") else vec
            preds  = self._iso_forest.predict(dense)
            for text, pred in zip(texts, preds):
                if pred == -1:
                    anomalies.append(text[:120])
                if len(anomalies) >= limit:
                    break
        except Exception as e:
            logger.debug(f"anomaly detection error: {e}")
        return anomalies

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    def _update_graph(self, text, label):
        if not NX_AVAILABLE or self._graph is None:
            return
        try:
            words  = self._tokenize(text)
            window = 4
            for i, word in enumerate(words):
                if not self._graph.has_node(word):
                    self._graph.add_node(word, weight=0, label=label)
                self._graph.nodes[word]["weight"] = (
                    self._graph.nodes[word].get("weight", 0) + 1
                )
                for j in range(i + 1, min(i + window, len(words))):
                    neighbor = words[j]
                    if self._graph.has_edge(word, neighbor):
                        self._graph[word][neighbor]["weight"] += 1
                    else:
                        self._graph.add_edge(word, neighbor, weight=1)
        except Exception as e:
            logger.debug(f"Graph update error: {e}")

    def get_top_concepts(self, n=20):
        """Return top concepts by node weight in knowledge graph."""
        if not NX_AVAILABLE or self._graph is None:
            return []
        try:
            nodes = [
                (node, data.get("weight", 0))
                for node, data in self._graph.nodes(data=True)
            ]
            nodes.sort(key=lambda x: x[1], reverse=True)
            return nodes[:n]
        except Exception:
            return []

    def get_related_concepts(self, concept, n=10):
        """Return concepts most connected to a given concept."""
        if not NX_AVAILABLE or self._graph is None:
            return []
        try:
            if concept not in self._graph:
                return []
            neighbors = [
                (nb, self._graph[concept][nb].get("weight", 0))
                for nb in self._graph.successors(concept)
            ]
            neighbors.sort(key=lambda x: x[1], reverse=True)
            return [n for n, _ in neighbors[:n]]
        except Exception:
            return []

    # ── Trend Detection ───────────────────────────────────────────────────────
    def _update_trends(self, text):
        date_key = datetime.utcnow().strftime("%Y-%m-%d")
        words    = self._tokenize(text)
        for word in words:
            if len(word) > 4:
                self._trend_data[word][date_key] += 1

    def get_trends(self, n=15):
        """
        Return rising and falling keywords comparing yesterday vs today.
        """
        today     = datetime.utcnow().strftime("%Y-%m-%d")
        from datetime import timedelta
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

        rising  = []
        falling = []

        for word, day_counts in self._trend_data.items():
            today_count     = day_counts.get(today, 0)
            yesterday_count = day_counts.get(yesterday, 0)
            if today_count > yesterday_count + 2:
                rising.append((word, today_count, yesterday_count))
            elif yesterday_count > today_count + 2:
                falling.append((word, today_count, yesterday_count))

        rising.sort(key=lambda x: x[1] - x[2], reverse=True)
        falling.sort(key=lambda x: x[2] - x[1], reverse=True)
        return {
            "rising":  rising[:n],
            "falling": falling[:n],
        }

    # ── Named Entity Extraction ───────────────────────────────────────────────
    def _extract_entities(self, text):
        """Regex-based NER: countries, organizations, people patterns."""
        try:
            # Capitalized multi-word sequences as potential proper nouns
            proper_nouns = re.findall(r"\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+)\b", text)
            for pn in proper_nouns:
                self._entities["proper_noun"].add(pn[:60])

            # CVE patterns
            cves = re.findall(r"\bCVE-\d{4}-\d{4,7}\b", text)
            for cve in cves:
                self._entities["cve"].add(cve)

            # URLs
            urls = re.findall(r"https?://[^\s\"'<>]+", text)
            for url in urls[:3]:
                self._entities["url"].add(url[:120])

            # Email addresses
            emails = re.findall(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", text)
            for email in emails:
                self._entities["email"].add(email)

            # Numbers with units (could be CVSS scores, stats)
            numbers = re.findall(r"\b\d+(?:\.\d+)? (?:percent|%|million|billion|CVE|USD|km|kg)\b", text)
            for num in numbers[:5]:
                self._entities["measurement"].add(num)
        except Exception as e:
            logger.debug(f"Entity extraction error: {e}")

    def get_entities(self, entity_type=None):
        """Return extracted named entities."""
        if entity_type:
            return list(self._entities.get(entity_type, set()))
        return {k: list(v)[:20] for k, v in self._entities.items()}

    # ── Auto-summarization ────────────────────────────────────────────────────
    def summarize(self, texts=None, n_sentences=5):
        """
        Extract key sentences using TF-IDF scores.
        If texts is None, summarizes the most recent corpus items.
        """
        if not SKLEARN_AVAILABLE:
            return "scikit-learn not available for summarization."

        with self._lock:
            corpus = texts or list(self._texts[-100:])

        if not corpus:
            return "No data to summarize."

        try:
            # Combine all text into sentences
            all_sentences = []
            for doc in corpus:
                sentences = re.split(r"[.!?]\s+", doc)
                all_sentences.extend([s.strip() for s in sentences if len(s.strip()) > 20])

            if len(all_sentences) < 2:
                return corpus[0][:300] if corpus else "No data."

            vec    = TfidfVectorizer(max_features=3000, stop_words="english")
            X      = vec.fit_transform(all_sentences)
            scores = np.asarray(X.sum(axis=1)).flatten()

            top_idx = scores.argsort()[::-1][:n_sentences]
            top_idx = sorted(top_idx)
            summary = " ".join(all_sentences[i] for i in top_idx)
            return summary[:1200]
        except Exception as e:
            logger.debug(f"Summarize error: {e}")
            return "Summarization failed."

    # ── Report builder ────────────────────────────────────────────────────────
    def _build_report(self, texts, labels):
        try:
            topics    = self.get_topics(6)
            clusters  = self.get_clusters()
            anomalies = self.get_anomalies(5)
            trends    = self.get_trends(8)
            concepts  = self.get_top_concepts(10)

            accuracy  = (self._correct / max(self._predictions, 1)) * 100
            label_dist = Counter(labels).most_common(8)

            self._report_cache = {
                "train_cycle":  self._train_count,
                "corpus_size":  len(texts),
                "categories":   len(set(labels)),
                "label_dist":   label_dist,
                "accuracy":     round(accuracy, 2),
                "topics":       topics,
                "clusters":     clusters,
                "anomalies":    anomalies,
                "trends":       trends,
                "top_concepts": concepts,
                "entities":     {k: list(v)[:5] for k, v in self._entities.items()},
                "confidence":   dict(self._confidence),
                "ts":           datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.debug(f"Report build error: {e}")

    def format_report(self):
        """Return a formatted human-readable learning report."""
        r = self._report_cache
        if not r:
            return "No learning report available yet."

        lines = [
            "🧠 *HELIX LEARNING ENGINE — REPORT*",
            f"🔄 Train Cycle: #{r.get('train_cycle', 0)}",
            f"📚 Corpus: {r.get('corpus_size', 0)} samples | "
            f"{r.get('categories', 0)} categories",
            f"🎯 Accuracy: {r.get('accuracy', 0):.1f}%",
            "━" * 35,
        ]

        # Topic modeling
        topics = r.get("topics", [])
        if topics:
            lines.append("\n📌 *TOP TOPICS (NMF)*")
            for t in topics[:6]:
                lines.append(f"  Topic {t['topic_id']}: {', '.join(t['words'][:6])}")

        # Trends
        trends = r.get("trends", {})
        rising  = trends.get("rising", [])
        falling = trends.get("falling", [])
        if rising:
            lines.append("\n📈 *RISING KEYWORDS*")
            for word, today, yest in rising[:6]:
                lines.append(f"  `{word}` +{today - yest} ({yest}→{today})")
        if falling:
            lines.append("\n📉 *FALLING KEYWORDS*")
            for word, today, yest in falling[:5]:
                lines.append(f"  `{word}` -{yest - today} ({yest}→{today})")

        # Anomalies
        anomalies = r.get("anomalies", [])
        if anomalies:
            lines.append("\n🚨 *ANOMALIES DETECTED*")
            for a in anomalies[:3]:
                lines.append(f"  • {a[:90]}")

        # Clusters
        clusters = r.get("clusters", {})
        if clusters:
            lines.append(f"\n🔵 *CLUSTERS*: {len(clusters)} event clusters found")

        # Top concepts
        concepts = r.get("top_concepts", [])
        if concepts:
            lines.append("\n💡 *TOP CONCEPTS (knowledge graph)*")
            lines.append("  " + ", ".join(
                f"{w}({c})" for w, c in concepts[:10]
            ))

        # Label distribution
        label_dist = r.get("label_dist", [])
        if label_dist:
            lines.append("\n📊 *CATEGORY DISTRIBUTION*")
            for label, count in label_dist[:8]:
                lines.append(f"  {label}: {count}")

        lines.append(f"\n⏱ `{r.get('ts', '')[:19]} UTC`")
        return "\n".join(lines)

    def get_report(self):
        return self._report_cache.copy()

    # ── State persistence ─────────────────────────────────────────────────────
    def _save_state(self):
        try:
            state = {
                "texts":       self._texts[-5000:],   # cap at 5000
                "labels":      self._labels[-5000:],
                "timestamps":  self._timestamps[-5000:],
                "pipe_nb":     self._pipe_nb,
                "pipe_sgd":    self._pipe_sgd,
                "pipe_rf":     self._pipe_rf,
                "nmf_model":   self._nmf_model,
                "nmf_tfidf":   self._nmf_tfidf,
                "kmeans":      self._kmeans,
                "tfidf_raw":   self._tfidf_raw,
                "iso_forest":  self._iso_forest,
                "confidence":  dict(self._confidence),
                "trend_data":  dict(self._trend_data),
                "entities":    {k: list(v) for k, v in self._entities.items()},
                "train_count": self._train_count,
                "predictions": self._predictions,
                "correct":     self._correct,
            }
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Model state saved to {MODEL_PATH}.")
        except Exception as e:
            logger.error(f"Save state error: {e}")

    def _load_state(self):
        if not MODEL_PATH.exists():
            logger.info("No previous model state found — starting fresh.")
            return
        try:
            with open(MODEL_PATH, "rb") as f:
                state = pickle.load(f)

            self._texts       = state.get("texts", [])
            self._labels      = state.get("labels", [])
            self._timestamps  = state.get("timestamps", [])
            self._pipe_nb     = state.get("pipe_nb")
            self._pipe_sgd    = state.get("pipe_sgd")
            self._pipe_rf     = state.get("pipe_rf")
            self._nmf_model   = state.get("nmf_model")
            self._nmf_tfidf   = state.get("nmf_tfidf")
            self._kmeans      = state.get("kmeans")
            self._tfidf_raw   = state.get("tfidf_raw")
            self._iso_forest  = state.get("iso_forest")
            self._train_count = state.get("train_count", 0)
            self._predictions = state.get("predictions", 0)
            self._correct     = state.get("correct", 0)

            for k, v in state.get("confidence", {}).items():
                self._confidence[k] = v
            for k, v in state.get("trend_data", {}).items():
                self._trend_data[k] = Counter(v)
            for k, v in state.get("entities", {}).items():
                self._entities[k] = set(v)

            logger.info(
                f"Loaded model state: {len(self._texts)} samples, "
                f"{self._train_count} prior training cycles."
            )
        except Exception as e:
            logger.error(f"Load state error: {e} — starting fresh.")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _tokenize(self, text):
        """Simple lowercase word tokenizer, removes stopwords."""
        STOP = {
            "the", "a", "an", "is", "in", "it", "of", "to", "and",
            "or", "for", "on", "at", "by", "be", "was", "are", "that",
            "this", "with", "from", "as", "has", "have", "had", "will",
            "not", "but", "its", "their", "they", "he", "she", "we",
            "you", "i", "said", "says", "after", "before", "also",
        }
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        return [w for w in words if w not in STOP]

    def stats(self):
        return {
            "corpus_size":    len(self._texts),
            "train_cycles":   self._train_count,
            "predictions":    self._predictions,
            "accuracy":       round(
                (self._correct / max(self._predictions, 1)) * 100, 2
            ),
            "graph_nodes":    self._graph.number_of_nodes() if self._graph else 0,
            "graph_edges":    self._graph.number_of_edges() if self._graph else 0,
            "sklearn_ready":  SKLEARN_AVAILABLE,
            "networkx_ready": NX_AVAILABLE,
            "running":        self._running,
        }
