"""
Helix Mythos — Core Configuration
MAXIMUM INTELLIGENCE MODE — Every domain, every source
"""

import os

# ─── Telegram ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8750159689:AAEeKYQ4VWseyGD1UPjIvXnxAYWRnN3keO8")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "8709046583")

# ─── Intelligence scan intervals ─────────────────────────────────────────────
FAST_INTERVAL_SECONDS   = 60
NORMAL_INTERVAL_SECONDS = 180     # 3 minutes — constant updates
SCAN_MODE               = "fast"  # Maximum speed

# ─── Memory ──────────────────────────────────────────────────────────────────
DB_PATH  = "helix_memory.db"
LOG_PATH = "helix_log.json"

# ─── Vision ──────────────────────────────────────────────────────────────────
CAMERA_INDEX         = 0
LIVE_CAMERA_INTERVAL = 30

# ─── Learning ────────────────────────────────────────────────────────────────
LEARNING_INTERVAL = 300   # retrain every 5 minutes

# ─── Helix identity ──────────────────────────────────────────────────────────
HELIX_NAME    = "Helix Mythos"
HELIX_VERSION = "2.0.0"
HELIX_MOTTO   = "All-Seeing. All-Knowing. Always Evolving."

# ─── MAXIMUM INTELLIGENCE FEED REGISTRY ──────────────────────────────────────
# Format: (Category, Source Name, RSS URL)
NEWS_FEEDS = [

    # ════════════════════════════════════════════════════════
    # WORLD NEWS — TOP TIER
    # ════════════════════════════════════════════════════════
    ("World",    "BBC World",         "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("World",    "BBC Top Stories",   "http://feeds.bbci.co.uk/news/rss.xml"),
    ("World",    "Reuters World",     "https://feeds.reuters.com/Reuters/worldNews"),
    ("World",    "Reuters Top",       "https://feeds.reuters.com/reuters/topNews"),
    ("World",    "AP Top News",       "https://rsshub.app/apnews/topics/ap-top-news"),
    ("World",    "Al Jazeera",        "https://www.aljazeera.com/xml/rss/all.xml"),
    ("World",    "CNN World",         "http://rss.cnn.com/rss/edition_world.rss"),
    ("World",    "CNN Top Stories",   "http://rss.cnn.com/rss/edition.rss"),
    ("World",    "Guardian World",    "https://www.theguardian.com/world/rss"),
    ("World",    "Guardian Top",      "https://www.theguardian.com/uk/rss"),
    ("World",    "NYT World",         "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("World",    "NYT Top Stories",   "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
    ("World",    "Washington Post",   "https://feeds.washingtonpost.com/rss/world"),
    ("World",    "The Independent",   "https://www.independent.co.uk/news/world/rss"),
    ("World",    "Sky News World",    "https://feeds.skynews.com/feeds/rss/world.xml"),
    ("World",    "France 24",         "https://www.france24.com/en/rss"),
    ("World",    "DW News",           "https://rss.dw.com/rdf/rss-en-all"),
    ("World",    "Euronews",          "https://www.euronews.com/rss"),
    ("World",    "NHK World",         "https://www3.nhk.or.jp/rss/news/cat0.xml"),
    ("World",    "Times of India",    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
    ("World",    "South China Post",  "https://www.scmp.com/rss/91/feed"),
    ("World",    "ABC News",          "https://feeds.abcnews.com/abcnews/topstories"),
    ("World",    "CBS News",          "https://www.cbsnews.com/latest/rss/main"),
    ("World",    "NBC News",          "https://feeds.nbcnews.com/nbcnews/public/news"),
    ("World",    "NPR News",          "https://feeds.npr.org/1001/rss.xml"),
    ("World",    "The Atlantic",      "https://www.theatlantic.com/feed/all/"),
    ("World",    "Axios",             "https://api.axios.com/feed/"),
    ("World",    "Politico",          "https://www.politico.com/rss/politicopicks.xml"),

    # ════════════════════════════════════════════════════════
    # GEOPOLITICS & CONFLICTS
    # ════════════════════════════════════════════════════════
    ("Geopolitics", "Reuters Defense",    "https://feeds.reuters.com/reuters/worldNews"),
    ("Geopolitics", "Defense One",        "https://www.defenseone.com/rss/all/"),
    ("Geopolitics", "War on the Rocks",   "https://warontherocks.com/feed/"),
    ("Geopolitics", "Foreign Policy",     "https://foreignpolicy.com/feed/"),
    ("Geopolitics", "Foreign Affairs",    "https://www.foreignaffairs.com/rss.xml"),
    ("Geopolitics", "The Diplomat",       "https://thediplomat.com/feed/"),
    ("Geopolitics", "Bellingcat",         "https://www.bellingcat.com/feed/"),
    ("Geopolitics", "Al Monitor",         "https://www.al-monitor.com/rss"),
    ("Geopolitics", "Middle East Eye",    "https://www.middleeasteye.net/rss"),
    ("Geopolitics", "RAND Corp",          "https://www.rand.org/pubs/research_briefs.xml"),
    ("Geopolitics", "Chatham House",      "https://www.chathamhouse.org/rss.xml"),

    # ════════════════════════════════════════════════════════
    # SCIENCE & RESEARCH
    # ════════════════════════════════════════════════════════
    ("Science",  "ScienceDaily Top",   "https://www.sciencedaily.com/rss/top/science.xml"),
    ("Science",  "ScienceDaily All",   "https://www.sciencedaily.com/rss/all.xml"),
    ("Science",  "Nature",             "https://www.nature.com/nature.rss"),
    ("Science",  "Science Magazine",   "https://www.science.org/rss/news_current.xml"),
    ("Science",  "New Scientist",      "https://www.newscientist.com/feed/home/"),
    ("Science",  "Scientific American","https://rss.sciam.com/ScientificAmerican-Global"),
    ("Science",  "PNAS",               "https://www.pnas.org/rss/current.xml"),
    ("Science",  "Cell",               "https://www.cell.com/cell/rss/current"),
    ("Science",  "The Scientist",      "https://www.the-scientist.com/rss"),
    ("Science",  "Phys.org",           "https://phys.org/rss-feed/"),
    ("Science",  "EurekAlert",         "https://www.eurekalert.org/rss.xml"),
    ("Science",  "Live Science",       "https://www.livescience.com/feeds/all"),
    ("Science",  "Popular Science",    "https://www.popsci.com/feed/"),
    ("Science",  "Quanta Magazine",    "https://www.quantamagazine.org/feed/"),
    ("Science",  "AAAS Science",       "https://www.science.org/action/showFeed?type=axatoc&feed=rss&jc=science"),

    # ════════════════════════════════════════════════════════
    # AI, MACHINE LEARNING & ROBOTICS
    # ════════════════════════════════════════════════════════
    ("AI_Tech",  "arXiv CS.AI",        "http://export.arxiv.org/rss/cs.AI"),
    ("AI_Tech",  "arXiv CS.LG",        "http://export.arxiv.org/rss/cs.LG"),
    ("AI_Tech",  "arXiv CS.RO",        "http://export.arxiv.org/rss/cs.RO"),
    ("AI_Tech",  "arXiv CS.CV",        "http://export.arxiv.org/rss/cs.CV"),
    ("AI_Tech",  "arXiv CS.NE",        "http://export.arxiv.org/rss/cs.NE"),
    ("AI_Tech",  "TechCrunch AI",      "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("AI_Tech",  "TechCrunch",         "https://techcrunch.com/feed/"),
    ("AI_Tech",  "VentureBeat AI",     "https://venturebeat.com/category/ai/feed/"),
    ("AI_Tech",  "MIT Tech Review",    "https://www.technologyreview.com/feed/"),
    ("AI_Tech",  "Wired Tech",         "https://www.wired.com/feed/rss"),
    ("AI_Tech",  "Hacker News",        "https://hnrss.org/frontpage"),
    ("AI_Tech",  "The Verge AI",       "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("AI_Tech",  "The Verge Tech",     "https://www.theverge.com/rss/index.xml"),
    ("AI_Tech",  "Ars Technica",       "https://feeds.arstechnica.com/arstechnica/index"),
    ("AI_Tech",  "ZDNet",              "https://www.zdnet.com/news/rss.xml"),
    ("AI_Tech",  "InfoQ AI",           "https://feed.infoq.com/"),
    ("AI_Tech",  "Google AI Blog",     "https://blog.google/technology/ai/rss/"),
    ("AI_Tech",  "OpenAI Blog",        "https://openai.com/blog/rss/"),
    ("AI_Tech",  "DeepMind Blog",      "https://www.deepmind.com/blog/rss.xml"),
    ("AI_Tech",  "Towards Data Sci",   "https://towardsdatascience.com/feed"),
    ("AI_Tech",  "Analytics Vidhya",   "https://www.analyticsvidhya.com/feed/"),
    ("AI_Tech",  "Import AI",          "https://importai.substack.com/feed"),
    ("AI_Tech",  "AI News",            "https://www.artificialintelligence-news.com/feed/"),

    # ════════════════════════════════════════════════════════
    # TECHNOLOGY & CYBERSECURITY
    # ════════════════════════════════════════════════════════
    ("Technology", "Krebs Security",   "https://krebsonsecurity.com/feed/"),
    ("Technology", "Dark Reading",     "https://www.darkreading.com/rss.xml"),
    ("Technology", "Threatpost",       "https://threatpost.com/feed/"),
    ("Technology", "SecurityWeek",     "https://www.securityweek.com/rss.xml"),
    ("Technology", "Schneier Security","https://www.schneier.com/feed/atom"),
    ("Technology", "GitHub Blog",      "https://github.blog/feed/"),
    ("Technology", "Stack Overflow",   "https://stackoverflow.blog/feed/"),
    ("Technology", "Dev.to",           "https://dev.to/feed"),
    ("Technology", "Slashdot",         "https://rss.slashdot.org/Slashdot/slashdotMain"),
    ("Technology", "Engadget",         "https://www.engadget.com/rss.xml"),
    ("Technology", "Gizmodo",          "https://gizmodo.com/rss"),
    ("Technology", "AnandTech",        "https://www.anandtech.com/rss/"),
    ("Technology", "Tom's Hardware",   "https://www.tomshardware.com/feeds/all"),

    # ════════════════════════════════════════════════════════
    # SPACE & ASTRONOMY
    # ════════════════════════════════════════════════════════
    ("Space",    "NASA Breaking News", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("Space",    "NASA News",          "https://www.nasa.gov/news-release/feed/"),
    ("Space",    "Space.com",          "https://www.space.com/feeds/all"),
    ("Space",    "SpaceNews",          "https://spacenews.com/feed/"),
    ("Space",    "Sky & Telescope",    "https://skyandtelescope.org/astronomy-news/feed/"),
    ("Space",    "ESA News",           "https://www.esa.int/rssfeed/Our_Activities/Space_Science"),
    ("Space",    "SpaceX",             "https://www.spacex.com/updates.json"),
    ("Space",    "Astronomy Now",      "https://astronomynow.com/feed/"),
    ("Space",    "arXiv Astrophysics", "http://export.arxiv.org/rss/astro-ph"),
    ("Space",    "Hubble News",        "https://hubblesite.org/api/v3/news?page=1&per_page=10&newstype=news"),
    ("Space",    "Universe Today",     "https://www.universetoday.com/feed/"),

    # ════════════════════════════════════════════════════════
    # HEALTH & MEDICINE
    # ════════════════════════════════════════════════════════
    ("Health",   "WHO News",           "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml"),
    ("Health",   "CDC Newsroom",       "https://tools.cdc.gov/api/v2/resources/media/316422.rss"),
    ("Health",   "NEJM",               "https://www.nejm.org/action/showFeed?jc=nejmresearch&type=etoc&feed=rss"),
    ("Health",   "The Lancet",         "https://www.thelancet.com/rssfeed/lancet_online.xml"),
    ("Health",   "BMJ",                "https://www.bmj.com/rss/bmj_current.xml"),
    ("Health",   "NIH News",           "https://www.nih.gov/news-events/news-releases/feed.xml"),
    ("Health",   "WebMD Health",       "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC"),
    ("Health",   "Medical Xpress",     "https://medicalxpress.com/rss-feed/"),
    ("Health",   "Health News",        "https://www.healthnewsreview.org/feed/"),
    ("Health",   "arXiv Biomedicine",  "http://export.arxiv.org/rss/q-bio"),
    ("Health",   "ScienceDaily Health","https://www.sciencedaily.com/rss/health_medicine.xml"),
    ("Health",   "MedPage Today",      "https://www.medpagetoday.com/rss/headlines.xml"),

    # ════════════════════════════════════════════════════════
    # ECONOMICS & FINANCE
    # ════════════════════════════════════════════════════════
    ("Finance",  "Bloomberg",          "https://feeds.bloomberg.com/markets/news.rss"),
    ("Finance",  "FT Markets",         "https://www.ft.com/rss/home"),
    ("Finance",  "WSJ Markets",        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("Finance",  "WSJ World",          "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("Finance",  "Reuters Business",   "https://feeds.reuters.com/reuters/businessNews"),
    ("Finance",  "CNBC Top News",      "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ("Finance",  "CNBC Markets",       "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"),
    ("Finance",  "MarketWatch",        "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Finance",  "The Economist",      "https://www.economist.com/finance-and-economics/rss.xml"),
    ("Finance",  "Forbes Business",    "https://www.forbes.com/business/feed2/"),
    ("Finance",  "Business Insider",   "https://feeds.businessinsider.com/custom/all"),
    ("Finance",  "Seeking Alpha",      "https://seekingalpha.com/feed.xml"),
    ("Finance",  "Zero Hedge",         "https://feeds.feedburner.com/zerohedge/feed"),
    ("Finance",  "IMF News",           "https://www.imf.org/en/News/rss?language=eng&category=PressReleases"),
    ("Finance",  "World Bank",         "https://blogs.worldbank.org/feed"),

    # ════════════════════════════════════════════════════════
    # CRYPTOCURRENCY & BLOCKCHAIN
    # ════════════════════════════════════════════════════════
    ("Crypto",   "CoinDesk",           "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Crypto",   "Cointelegraph",      "https://cointelegraph.com/rss"),
    ("Crypto",   "Decrypt",            "https://decrypt.co/feed"),
    ("Crypto",   "Bitcoin Magazine",   "https://bitcoinmagazine.com/feed"),
    ("Crypto",   "The Block",          "https://www.theblock.co/rss.xml"),
    ("Crypto",   "CryptoSlate",        "https://cryptoslate.com/feed/"),
    ("Crypto",   "Blockworks",         "https://blockworks.co/feed/"),

    # ════════════════════════════════════════════════════════
    # CLIMATE & ENVIRONMENT
    # ════════════════════════════════════════════════════════
    ("Climate",  "Guardian Climate",   "https://www.theguardian.com/environment/climate-crisis/rss"),
    ("Climate",  "BBC Climate",        "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("Climate",  "Climate Home News",  "https://www.climatechangenews.com/feed/"),
    ("Climate",  "Carbon Brief",       "https://www.carbonbrief.org/feed"),
    ("Climate",  "NOAA Climate",       "https://www.climate.gov/feeds/news-features.rss"),
    ("Climate",  "NASA Climate",       "https://climate.nasa.gov/news/rss.xml"),
    ("Climate",  "Yale Climate",       "https://e360.yale.edu/feed"),
    ("Climate",  "Inside Climate News","https://insideclimatenews.org/feed/"),
    ("Climate",  "ScienceDaily Env",   "https://www.sciencedaily.com/rss/earth_climate.xml"),

    # ════════════════════════════════════════════════════════
    # POLITICS & GOVERNMENT
    # ════════════════════════════════════════════════════════
    ("Politics", "Politico EU",        "https://www.politico.eu/feed/"),
    ("Politics", "The Hill",           "https://thehill.com/rss/syndicator/19110"),
    ("Politics", "Roll Call",          "https://rollcall.com/feed/"),
    ("Politics", "BBC Politics",       "https://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("Politics", "CNN Politics",       "http://rss.cnn.com/rss/cnn_allpolitics.rss"),
    ("Politics", "Reuters Politics",   "https://feeds.reuters.com/Reuters/PoliticsNews"),
    ("Politics", "Axios Politics",     "https://api.axios.com/feed/"),

    # ════════════════════════════════════════════════════════
    # NATURAL DISASTERS & EMERGENCY
    # ════════════════════════════════════════════════════════
    ("Disasters","USGS Earthquakes",   "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.atom"),
    ("Disasters","ReliefWeb",          "https://reliefweb.int/headlines/rss.xml"),
    ("Disasters","UN OCHA",            "https://www.unocha.org/feed"),
    ("Disasters","Floodlist",          "https://floodlist.com/feed"),
    ("Disasters","Volcano Discovery",  "https://www.volcanodiscovery.com/volcano-news.rss"),
    ("Disasters","GDACS",              "https://www.gdacs.org/xml/rss.xml"),

    # ════════════════════════════════════════════════════════
    # ENERGY & RESOURCES
    # ════════════════════════════════════════════════════════
    ("Energy",   "Oil Price",          "https://oilprice.com/rss/main"),
    ("Energy",   "Energy Monitor",     "https://www.energymonitor.ai/feed/"),
    ("Energy",   "Renewable Energy",   "https://www.renewableenergyworld.com/feed/"),
    ("Energy",   "World Nuclear News", "https://www.world-nuclear-news.org/rss"),
    ("Energy",   "PV Magazine",        "https://www.pv-magazine.com/feed/"),

    # ════════════════════════════════════════════════════════
    # MILITARY & DEFENSE
    # ════════════════════════════════════════════════════════
    ("Military", "Defense News",       "https://www.defensenews.com/arc/outboundfeeds/rss/"),
    ("Military", "Janes",              "https://www.janes.com/feeds/news"),
    ("Military", "Task & Purpose",     "https://taskandpurpose.com/feed/"),
    ("Military", "Breaking Defense",   "https://breakingdefense.com/feed/"),
    ("Military", "USNI News",          "https://news.usni.org/feed"),
    ("Military", "Army Times",         "https://www.armytimes.com/arc/outboundfeeds/rss/"),

    # ════════════════════════════════════════════════════════
    # ACADEMIA & RESEARCH PREPRINTS
    # ════════════════════════════════════════════════════════
    ("Research", "arXiv Physics",      "http://export.arxiv.org/rss/physics"),
    ("Research", "arXiv Math",         "http://export.arxiv.org/rss/math"),
    ("Research", "arXiv Quantum",      "http://export.arxiv.org/rss/quant-ph"),
    ("Research", "arXiv Bio",          "http://export.arxiv.org/rss/q-bio.PE"),
    ("Research", "arXiv Econ",         "http://export.arxiv.org/rss/econ"),
    ("Research", "SSRN",               "https://papers.ssrn.com/sol3/Jrnls/rss.cfm?link=0&jrnl=0&stype=0"),
    ("Research", "PubMed Latest",      "https://pubmed.ncbi.nlm.nih.gov/rss/search/1-AyC8vR3PjZW6yfMYxdqm6FzSdVMPlBOVCJtTB0YXtTHLKkFH4/?limit=20&utm_campaign=pubmed-2&fc=20231107175526"),

    # ════════════════════════════════════════════════════════
    # SOCIAL & CULTURAL
    # ════════════════════════════════════════════════════════
    ("Culture",  "BBC Culture",        "http://feeds.bbci.co.uk/culture/rss.xml"),
    ("Culture",  "Smithsonian",        "https://www.smithsonianmag.com/rss/"),
    ("Culture",  "Aeon",               "https://aeon.co/feed.rss"),
    ("Culture",  "Nautilus",           "https://nautil.us/feed/"),
    ("Culture",  "The Conversation",   "https://theconversation.com/us/articles.atom"),
    ("Culture",  "Wired Ideas",        "https://www.wired.com/feed/category/ideas/latest/rss"),
    ("Culture",  "Reddit World News",  "https://www.reddit.com/r/worldnews/top/.rss?t=day"),
    ("Culture",  "Reddit Science",     "https://www.reddit.com/r/science/top/.rss?t=day"),
    ("Culture",  "Reddit Technology",  "https://www.reddit.com/r/technology/top/.rss?t=day"),
    ("Culture",  "Reddit Futurology",  "https://www.reddit.com/r/Futurology/top/.rss?t=day"),
]

# ─── Agent names ─────────────────────────────────────────────────────────────
AGENTS = [
    "PlannerAgent", "ResearchAgent", "CodingAgent",
    "VisionAgent",  "LearningAgent", "AutomationAgent", "IntelligenceAgent",
]

# ─── Category display order ───────────────────────────────────────────────────
CATEGORY_ORDER = [
    "World", "Geopolitics", "Military", "Politics",
    "Finance", "Crypto", "Economy",
    "Science", "Research", "Health",
    "AI_Tech", "Technology",
    "Space", "Climate", "Energy",
    "Disasters", "Culture",
]

CATEGORY_EMOJI = {
    "World":       "🌍",
    "Geopolitics": "🎯",
    "Military":    "⚔️",
    "Politics":    "🏛️",
    "Finance":     "💰",
    "Crypto":      "₿",
    "Science":     "🔬",
    "Research":    "📄",
    "Health":      "🏥",
    "AI_Tech":     "🤖",
    "Technology":  "💻",
    "Space":       "🚀",
    "Climate":     "🌡️",
    "Energy":      "⚡",
    "Disasters":   "🚨",
    "Culture":     "🎭",
}
