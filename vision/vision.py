"""
Helix Mythos — Vision Engine
YOLOv8 object detection · Face detection · Motion detection ·
Scene classification · OCR · Emotion placeholders · Live Telegram feed
"""

import io
import time
import logging
import threading
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logger = logging.getLogger("HelixVision")

# ── Optional heavy imports — all gracefully degraded ─────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
    logger.info("OpenCV available.")
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Vision will be limited.")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available.")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logger.info("Ultralytics YOLO available.")
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics not installed. Falling back to basic OpenCV detection.")

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
    logger.info("face_recognition available.")
except ImportError:
    FACE_REC_AVAILABLE = False
    logger.warning("face_recognition not available. Using Haar cascade fallback.")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    logger.info("pytesseract available.")
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available. OCR disabled.")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available.")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# ── Alert object classes for YOLO ────────────────────────────────────────────
ALERT_CLASSES = {"person", "knife", "scissors", "fire", "gun", "weapon", "pistol", "rifle"}

# ── Color palette for bounding boxes (BGR for OpenCV) ────────────────────────
CLASS_COLORS = {
    "person":    (0, 255, 0),
    "car":       (255, 165, 0),
    "truck":     (255, 100, 0),
    "bus":       (200, 80, 0),
    "dog":       (255, 255, 0),
    "cat":       (255, 200, 0),
    "knife":     (0, 0, 255),
    "gun":       (0, 0, 200),
    "fire":      (0, 100, 255),
    "default":   (100, 200, 255),
}


class VisionEngine:
    def __init__(self, notify_callback=None):
        self.notify         = notify_callback
        self._running       = False
        self._thread        = None
        self._yolo          = None
        self._haar_face     = None
        self._last_frame    = None
        self._prev_frame    = None
        self._frame_count   = 0
        self._fps           = 0.0
        self._fps_ts        = time.time()
        self._last_send_ts  = 0.0
        self._send_interval = 999999     # Never auto-send — only on /camera command
        self._alert_cooldown = {}
        self._alert_interval = 30        # seconds between repeat alerts

        self._load_models()

    # ── Model loading ─────────────────────────────────────────────────────────
    def _load_models(self):
        if YOLO_AVAILABLE:
            try:
                self._yolo = YOLO("yolov8n.pt")   # auto-downloads on first run
                logger.info("YOLOv8n model loaded.")
            except Exception as e:
                logger.error(f"YOLO load error: {e}")
                self._yolo = None

        if CV2_AVAILABLE:
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self._haar_face = cv2.CascadeClassifier(cascade_path)
                logger.info("Haar cascade face detector loaded.")
            except Exception as e:
                logger.error(f"Haar cascade load error: {e}")

    # ── Public API ────────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._live_loop, daemon=True, name="Vision"
        )
        self._thread.start()
        logger.info("Vision Engine started — live video loop running.")

    def stop(self):
        self._running = False

    # ── Live video loop ───────────────────────────────────────────────────────
    def _live_loop(self):
        if not CV2_AVAILABLE:
            logger.error("OpenCV unavailable — live loop cannot start.")
            return

        cap = None
        while self._running:
            try:
                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(config.CAMERA_INDEX)
                    if not cap.isOpened():
                        logger.warning("Camera not available. Retrying in 10s...")
                        time.sleep(10)
                        continue

                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning("Empty frame — retrying.")
                    time.sleep(1)
                    continue

                self._frame_count += 1
                now = time.time()

                # FPS estimation
                elapsed = now - self._fps_ts
                if elapsed >= 2.0:
                    self._fps     = self._frame_count / elapsed
                    self._fps_ts  = now
                    self._frame_count = 0

                # Motion detection
                motion_detected, motion_level = self._detect_motion(frame)
                self._prev_frame = frame.copy()

                # Detection pipeline
                detections   = self._run_detection(frame)
                faces        = self._detect_faces(frame)
                scene        = self._classify_scene(frame)
                emotion_info = self._estimate_emotions(frame, faces)

                # Draw all annotations onto frame
                annotated = self._draw_annotations(
                    frame, detections, faces, scene,
                    motion_detected, motion_level, emotion_info
                )
                self._last_frame = annotated

                # Object alert system
                self._check_alerts(detections)

                # Send to Telegram every N seconds
                if now - self._last_send_ts >= self._send_interval:
                    self._last_send_ts = now
                    jpg_bytes = self._encode_jpg(annotated)
                    if jpg_bytes and self.notify:
                        caption = self._build_caption(
                            detections, scene, motion_detected, faces
                        )
                        try:
                            self.notify(jpg_bytes, caption=caption)
                        except Exception as e:
                            logger.debug(f"Frame send error: {e}")

            except Exception as e:
                logger.error(f"Live loop error: {e}")
                time.sleep(2)

        if cap is not None:
            cap.release()

    # ── Detection methods ─────────────────────────────────────────────────────
    def _run_detection(self, frame):
        """Run YOLO or fallback detection. Returns list of detection dicts."""
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            return []

        if self._yolo is not None:
            return self._run_yolo(frame)
        else:
            return self._run_haar_objects(frame)

    def _run_yolo(self, frame):
        detections = []
        try:
            results = self._yolo(frame, verbose=False)
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    conf  = float(box.conf[0])
                    cls   = int(box.cls[0])
                    label = self._yolo.names.get(cls, "unknown")
                    x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                    detections.append({
                        "label": label,
                        "conf":  conf,
                        "bbox":  (x1, y1, x2, y2),
                    })
        except Exception as e:
            logger.debug(f"YOLO inference error: {e}")
        return detections

    def _run_haar_objects(self, frame):
        """Basic fallback: detect faces as 'person' via Haar cascade."""
        detections = []
        if self._haar_face is None:
            return detections
        try:
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._haar_face.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            for (x, y, w, h) in faces:
                detections.append({
                    "label": "person",
                    "conf":  0.80,
                    "bbox":  (x, y, x + w, y + h),
                })
        except Exception as e:
            logger.debug(f"Haar detection error: {e}")
        return detections

    def _detect_faces(self, frame):
        """Dedicated face detection with optional face_recognition encoding."""
        faces = []
        if not CV2_AVAILABLE:
            return faces

        if FACE_REC_AVAILABLE:
            try:
                rgb        = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locations  = face_recognition.face_locations(rgb, model="hog")
                encodings  = face_recognition.face_encodings(rgb, locations)
                for (top, right, bottom, left), enc in zip(locations, encodings):
                    faces.append({
                        "bbox":     (left, top, right, bottom),
                        "encoding": enc,
                        "label":    "face",
                    })
                return faces
            except Exception as e:
                logger.debug(f"face_recognition error: {e}")

        # Haar cascade fallback
        if self._haar_face is None:
            return faces
        try:
            gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detects = self._haar_face.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            for (x, y, w, h) in detects:
                faces.append({
                    "bbox":     (x, y, x + w, y + h),
                    "encoding": None,
                    "label":    "face",
                })
        except Exception as e:
            logger.debug(f"Haar face detect error: {e}")
        return faces

    # ── Scene classification ──────────────────────────────────────────────────
    def _classify_scene(self, frame):
        """Classify scene as indoor/outdoor/dark/bright using pixel stats."""
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            return "unknown"
        try:
            hsv        = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mean_v     = float(np.mean(hsv[:, :, 2]))
            mean_s     = float(np.mean(hsv[:, :, 1]))
            mean_blue  = float(np.mean(frame[:, :, 0]))
            mean_green = float(np.mean(frame[:, :, 1]))

            if mean_v < 50:
                return "dark"
            if mean_v > 210:
                return "bright"
            if mean_blue > mean_green * 0.9 and mean_s < 80:
                return "outdoor (sky visible)"
            if mean_green > mean_blue * 1.1:
                return "outdoor (vegetation)"
            return "indoor"
        except Exception:
            return "unknown"

    # ── Motion detection ──────────────────────────────────────────────────────
    def _detect_motion(self, frame):
        """Compare current frame with previous. Returns (motion_bool, level%)."""
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            return False, 0.0
        if self._prev_frame is None:
            return False, 0.0
        try:
            prev_gray = cv2.cvtColor(self._prev_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(frame,             cv2.COLOR_BGR2GRAY)
            diff      = cv2.absdiff(prev_gray, curr_gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            motion_px = float(np.sum(thresh > 0))
            total_px  = float(thresh.size)
            level     = (motion_px / total_px) * 100.0
            return level > 1.5, round(level, 2)
        except Exception:
            return False, 0.0

    # ── Emotion placeholder ───────────────────────────────────────────────────
    def _estimate_emotions(self, frame, faces):
        """
        Emotion estimation using facial landmark heuristics.
        Returns list of emotion strings, one per face.
        Placeholder hook for future torch/dlib integration.
        """
        emotions = []
        for face in faces:
            emotion = "neutral"
            if CV2_AVAILABLE and NUMPY_AVAILABLE:
                try:
                    x1, y1, x2, y2 = face["bbox"]
                    roi  = frame[y1:y2, x1:x2]
                    if roi.size == 0:
                        emotions.append(emotion)
                        continue
                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    mean = float(np.mean(gray))
                    std  = float(np.std(gray))
                    # Rough heuristic
                    if std < 15:
                        emotion = "calm"
                    elif mean > 190:
                        emotion = "surprised"
                    elif std > 65:
                        emotion = "active"
                    elif mean < 80:
                        emotion = "tense"
                except Exception:
                    pass
            emotions.append(emotion)
        return emotions

    # ── Drawing annotations ───────────────────────────────────────────────────
    def _draw_annotations(
        self, frame, detections, faces, scene,
        motion_detected, motion_level, emotion_info
    ):
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            return frame

        output = frame.copy()
        h, w   = output.shape[:2]
        ts_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Draw YOLO / detection bounding boxes
        for det in detections:
            label = det["label"]
            conf  = det["conf"]
            x1, y1, x2, y2 = det["bbox"]
            color = CLASS_COLORS.get(label, CLASS_COLORS["default"])
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            text        = f"{label} {conf * 100:.0f}%"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(output, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            cv2.putText(output, text, (x1 + 2, y1 - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

        # Draw face boxes (blue) with emotion label
        for idx, face in enumerate(faces):
            fx1, fy1, fx2, fy2 = face["bbox"]
            emotion = emotion_info[idx] if idx < len(emotion_info) else "neutral"
            cv2.rectangle(output, (fx1, fy1), (fx2, fy2), (255, 80, 80), 2)
            cv2.putText(output, f"face:{emotion}", (fx1, max(fy1 - 5, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 80, 80), 1, cv2.LINE_AA)

        # HUD top bar
        cv2.rectangle(output, (0, 0), (w, 54), (20, 20, 20), -1)
        cv2.putText(output, f"HELIX VISION | {ts_str}",
                    (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 150), 1)
        cv2.putText(
            output,
            f"FPS:{self._fps:.1f}  Obj:{len(detections)}  Face:{len(faces)}  Scene:{scene}",
            (8, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 200, 200), 1
        )

        # Object count badge (bottom-left)
        badge_text = f"{len(detections)} objects detected"
        cv2.rectangle(output, (0, h - 28), (len(badge_text) * 9 + 10, h), (40, 40, 40), -1)
        cv2.putText(output, badge_text,
                    (6, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)

        # Motion indicator (top-right)
        if motion_detected:
            cv2.putText(output, f"MOTION {motion_level:.1f}%",
                        (w - 165, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 80, 255), 2)
            cv2.rectangle(output, (w - 5, 0), (w, h), (0, 0, 255), 5)

        return output

    # ── Alert system ──────────────────────────────────────────────────────────
    def _check_alerts(self, detections):
        now = time.time()
        for det in detections:
            label = det["label"].lower()
            if label in ALERT_CLASSES:
                last = self._alert_cooldown.get(label, 0)
                if now - last > self._alert_interval:
                    self._alert_cooldown[label] = now
                    msg = (
                        f"⚠️ *VISION ALERT*\n"
                        f"Detected: `{label}` ({det['conf']*100:.0f}% confidence)\n"
                        f"🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}"
                    )
                    logger.warning(f"Alert triggered: {label} detected!")
                    if self.notify:
                        try:
                            self.notify(msg, is_text=True)
                        except Exception as e:
                            logger.debug(f"Alert send error: {e}")

    # ── Caption builder ───────────────────────────────────────────────────────
    def _build_caption(self, detections, scene, motion_detected, faces):
        ts   = datetime.utcnow().strftime("%H:%M:%S UTC")
        objs = ", ".join(
            f"{d['label']}({d['conf']*100:.0f}%)" for d in detections[:6]
        ) or "none"
        lines = [
            f"👁 *Helix Vision Frame* | {ts}",
            f"🏷 Objects: `{objs}`",
            f"😐 Faces: `{len(faces)}`",
            f"🌄 Scene: `{scene}`",
            f"⚡ FPS: `{self._fps:.1f}`",
        ]
        if motion_detected:
            lines.append("🔴 *Motion Detected*")
        return "\n".join(lines)

    # ── Screenshot + OCR ─────────────────────────────────────────────────────
    def capture_screenshot(self):
        """
        Capture a screenshot of the primary display using pyautogui,
        run OCR with pytesseract, and return annotated JPEG bytes.
        """
        try:
            import pyautogui
        except ImportError:
            logger.warning("pyautogui not available — screenshot disabled.")
            return None

        try:
            pil_img = pyautogui.screenshot()
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None

        ocr_text = ""
        if TESSERACT_AVAILABLE:
            try:
                ocr_text = pytesseract.image_to_string(pil_img)[:500]
            except Exception as e:
                logger.debug(f"OCR error: {e}")

        # Convert PIL to OpenCV and annotate
        if CV2_AVAILABLE and NUMPY_AVAILABLE:
            frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            ts    = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            cv2.putText(frame, f"SCREENSHOT | {ts}",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 150), 2)
            if ocr_text:
                for i, line in enumerate(ocr_text.split("\n")[:3], 1):
                    cv2.putText(frame, f"OCR: {line[:60]}",
                                (10, 28 + i * 24), cv2.FONT_HERSHEY_SIMPLEX,
                                0.45, (200, 200, 0), 1)
            return self._encode_jpg(frame)

        if PIL_AVAILABLE:
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=80)
            return buf.getvalue()

        return None

    def get_ocr_text(self):
        """Capture screen and return OCR text only."""
        if not TESSERACT_AVAILABLE:
            return "pytesseract not available — install it and Tesseract OCR."
        try:
            import pyautogui
            pil_img = pyautogui.screenshot()
            return pytesseract.image_to_string(pil_img)
        except Exception as e:
            return f"OCR error: {e}"

    # ── Frame access / snapshot ───────────────────────────────────────────────
    def capture_frame(self):
        """
        Capture a single annotated camera frame and return JPEG bytes.
        Used for on-demand snapshots without the live loop running.
        """
        if not CV2_AVAILABLE:
            return None
        try:
            cap = cv2.VideoCapture(config.CAMERA_INDEX)
            if not cap.isOpened():
                logger.warning("Camera not available for snapshot.")
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                return None

            detections          = self._run_detection(frame)
            faces               = self._detect_faces(frame)
            scene               = self._classify_scene(frame)
            motion, mlvl        = self._detect_motion(frame)
            emotions            = self._estimate_emotions(frame, faces)
            annotated           = self._draw_annotations(
                frame, detections, faces, scene, motion, mlvl, emotions
            )
            return self._encode_jpg(annotated)
        except Exception as e:
            logger.error(f"Capture frame error: {e}")
            return None

    def get_last_frame(self):
        """Return the most recently captured annotated frame as JPEG bytes."""
        if self._last_frame is None:
            return None
        return self._encode_jpg(self._last_frame)

    # ── Utility ───────────────────────────────────────────────────────────────
    def _encode_jpg(self, frame, quality=80):
        if not CV2_AVAILABLE or frame is None:
            return None
        try:
            ret, buf = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            return bytes(buf) if ret else None
        except Exception as e:
            logger.debug(f"JPEG encode error: {e}")
            return None

    def stats(self):
        return {
            "yolo_available":      self._yolo is not None,
            "face_rec_available":  FACE_REC_AVAILABLE,
            "opencv_available":    CV2_AVAILABLE,
            "tesseract_available": TESSERACT_AVAILABLE,
            "fps":                 round(self._fps, 2),
            "running":             self._running,
        }
