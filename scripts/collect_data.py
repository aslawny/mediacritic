#!/usr/bin/env python3
"""
MediaCritic -- Collecte de donnees catalogue
Sources : iTunes Search API (gratuit), YouTube Data API v3, Spotify API
Usage   : python collect_data.py [--mode podcast|youtube|all] [--youtube-key KEY]
"""

import json, os, re, time, urllib.request, urllib.parse, hashlib, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests as _requests_lib
    def _http_get(url, params=None, headers=None, timeout=15):
        r = _requests_lib.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
except ImportError:
    _requests_lib = None
    def _http_get(url, params=None, headers=None, timeout=15):
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

# --- Chemins ------------------------------------------------------------------
ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data" / "content"
CATALOG_OUT = ROOT / "data" / "catalog.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- Episodes MediaCritic -----------------------------------------------------
MEDIACRITIC_EPISODES = [
    {"ep": 1,  "slug": "la-5e-de-couv",             "title": "La 5e de Couv'",            "type": "podcast", "categories": ["livres","culture"],            "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 2,  "slug": "lesprit-critique",           "title": "L'Esprit Critique",         "type": "podcast", "categories": ["sciences","societe"],          "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 3,  "slug": "hardisk-stories",            "title": "Hardisk Stories",            "type": "podcast", "categories": ["tech","geek"],                 "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 4,  "slug": "le-podcast-du-weekend",      "title": "Le Podcast du Weekend",      "type": "podcast", "categories": ["culture","actualite"],         "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 5,  "slug": "braincast",                  "title": "BrainCast",                  "type": "podcast", "categories": ["sciences","vulgarisation"],    "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 6,  "slug": "floodcast",                  "title": "Floodcast",                  "type": "podcast", "categories": ["gaming","culture geek"],       "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 7,  "slug": "fin-du-game",                "title": "Fin du Game",                "type": "podcast", "categories": ["gaming"],                      "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 8,  "slug": "blockbusters",               "title": "BlockBusters",               "type": "podcast", "categories": ["cinema","series"],             "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 9,  "slug": "la-story-des-echos",         "title": "La Story des Echos",         "type": "podcast", "categories": ["economie","business"],         "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 10, "slug": "le-rendez-vous-tech",        "title": "Le Rendez-vous Tech",        "type": "podcast", "categories": ["tech","numerique"],            "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 11, "slug": "emotions",                   "title": "Emotions",                   "type": "podcast", "categories": ["bien-etre","psychologie"],     "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 12, "slug": "safepace",                   "title": "SafePace",                   "type": "podcast", "categories": ["sport","running","endurance"],  "itunes_id": None, "spotify_show": "7AH8nT1CoTmV1MfhxyTl3n", "youtube": None},
    {"ep": 13, "slug": "entrez-dans-lhistoire",      "title": "Entrez dans l'Histoire",    "type": "podcast", "categories": ["histoire"],                    "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 14, "slug": "seldell",                    "title": "Seldell",                    "type": "youtube", "categories": ["gaming","jeux inde"],           "itunes_id": None, "spotify_show": None,                      "youtube": "@seldell"},
    {"ep": 15, "slug": "passion-renovation",         "title": "Passion Renovation",         "type": "youtube", "categories": ["renovation","DIY","maison"],   "itunes_id": None, "spotify_show": None,                      "youtube": "@passionrenovation"},
    {"ep": 16, "slug": "chef-otaku",                 "title": "Chef Otaku",                 "type": "youtube", "categories": ["cuisine","anime","culture"],   "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 17, "slug": "lheure-du-crime",            "title": "L'Heure du Crime",          "type": "podcast", "categories": ["true crime","societe"],        "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 18, "slug": "on-va-deguster",             "title": "On va deguster",             "type": "podcast", "categories": ["gastronomie","cuisine"],       "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 19, "slug": "silicon-carne",              "title": "Silicon Carne",              "type": "podcast", "categories": ["tech","humour"],               "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 20, "slug": "extraterrien",               "title": "Extraterrien",               "type": "podcast", "categories": ["sport","societe"],             "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 21, "slug": "lafter-foot",                "title": "L'After Foot",              "type": "podcast", "categories": ["football","sport"],            "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 22, "slug": "notabene",                   "title": "NotaBene",                   "type": "youtube", "categories": ["histoire","geopolitique"],     "itunes_id": None, "spotify_show": None,                      "youtube": "@nota.bene"},
    {"ep": 23, "slug": "re-take",                    "title": "Re-Take",                    "type": "youtube", "categories": ["gaming","critique"],           "itunes_id": None, "spotify_show": None,                      "youtube": "@Retake"},
    {"ep": 24, "slug": "cest-plus-complique-que-ca", "title": "C'est plus complique que ca","type": "podcast","categories": ["histoire","societe"],          "itunes_id": None, "spotify_show": "1pvsIBHWTfk9aROklANap8",  "youtube": None},
    {"ep": 25, "slug": "le-joueur-du-grenier",       "title": "Le Joueur du Grenier",       "type": "youtube", "categories": ["gaming","retro","nostalgie"],  "itunes_id": None, "spotify_show": None,                      "youtube": "@joueurdugrenier"},
    {"ep": 26, "slug": "quelle-histoire",            "title": "Quelle Histoire",            "type": "podcast", "categories": ["histoire","enfants","education"],"itunes_id":None, "spotify_show": "76IarJo3W3YmD3e9V43wD0",  "youtube": "@quellehistoire_podcast"},
]

# --- Chaines YouTube curees ---------------------------------------------------
YOUTUBE_CHANNELS = [
    # (handle, slug, title, categories)
    ("@LeMondeOfficiel",      "le-monde",                 "Le Monde",                    ["actualite","news"]),
    ("@franceinfo",           "france-info-yt",           "franceinfo",                  ["actualite","news"]),
    ("@BFMTV",                "bfmtv",                    "BFMTV",                       ["actualite","news"]),
    ("@franceinter",          "france-inter-yt",          "France Inter",                ["actualite","culture"]),
    ("@LCP",                  "lcp",                      "LCP",                         ["actualite","politique"]),
    ("@LeMonde",              "le-monde-video",           "Le Monde Video",              ["actualite","societe"]),
    ("@mediapart",            "mediapart",                "Mediapart",                   ["actualite","societe"]),
    ("@nota.bene",            "notabene",                 "NotaBene",                    ["histoire","geopolitique"]),
    ("@Nota.Bene.History",    "notabene-history",         "NotaBene History",            ["histoire"]),
    ("@AstronoGeek",          "astronomgeek",             "AstronoGeek",                 ["sciences","espace"]),
    ("@scienceetonnante",     "science-etonnante",        "Science Etonnante",           ["sciences","vulgarisation"]),
    ("@cestpassorcier",       "cest-pas-sorcier",         "C'est pas sorcier",          ["sciences","education"]),
    ("@e-penser",             "e-penser",                 "e-penser",                    ["sciences","philosophie"]),
    ("@Kurzgesagt",           "kurzgesagt-fr",            "Kurzgesagt FR",               ["sciences","vulgarisation"]),
    ("@dirtybiology",         "dirty-biology",            "DirtyBiology",                ["sciences","biologie"]),
    ("@LeReveilleur",         "le-revilleur",             "Le Revilleur",                ["sciences","energie"]),
    ("@Hygiene_Mentale",      "hygiene-mentale",          "Hygiene Mentale",             ["sciences","philosophie"]),
    ("@videodechat",          "video-de-chat",            "Video de Chat",               ["humour","comedie"]),
    ("@joueurdugrenier",      "le-joueur-du-grenier",     "Le Joueur du Grenier",        ["gaming","retro","nostalgie"]),
    ("@Seldell",              "seldell",                  "Seldell",                     ["gaming","jeux inde"]),
    ("@Retake",               "re-take",                  "Re-Take",                     ["gaming","critique"]),
    ("@MontesinosPierre",     "pierre-montesinos",        "Pierre Montesinos",           ["gaming"]),
    ("@Benzaie",              "benzaie",                  "Benzaie",                     ["gaming","culture geek"]),
    ("@Balade_Mentale",       "balade-mentale",           "Balade Mentale",              ["psychologie","bien-etre"]),
    ("@Axolot",               "axolot",                   "Axolot",                      ["culture","curiosites"]),
    ("@LaCinetek",            "la-cinetek",               "La Cinetek",                  ["cinema","culture"]),
    ("@CritiquePlusCinema",   "critique-plus",            "Critique +",                  ["cinema","series"]),
    ("@PresentationNight",    "presentation-night",       "Presentation Night",          ["cinema","animation"]),
    ("@PassionRenovation",    "passion-renovation",       "Passion Renovation",          ["renovation","DIY","maison"]),
    ("@ChefOtakuOfficial",    "chef-otaku",               "Chef Otaku",                  ["cuisine","anime"]),
    ("@750g",                 "750g",                     "750g",                        ["gastronomie","cuisine"]),
    ("@FinDuGame",            "fin-du-game-yt",           "Fin du Game",                 ["gaming"]),
    ("@HugoDecrypte",         "hugo-decrypte",            "HugoDecrypte",                ["actualite","societe"]),
    ("@Osons_Causer",         "osons-causer",             "Osons Causer",                ["politique","societe"]),
    ("@LaPrimaire",           "la-primaire",              "La Primaire",                 ["politique","societe"]),
    ("@Blast_info",           "blast",                    "Blast",                       ["actualite","societe"]),
    ("@Bricevido",            "brice-vido",               "Brice Vido",                  ["sport","football"]),
    ("@Thibaud_Velo",         "thibaud-velo",             "Thibaud Velo",                ["sport","cyclisme"]),
    ("@AthleteFactory",       "athlete-factory",          "Athlete Factory",             ["sport","running"]),
    ("@HistoireEtCivilisation","histoire-et-civilisation","Histoire et Civilisation",    ["histoire"]),
    ("@histoirebreve",        "histoire-breve",           "Histoire Breve",              ["histoire"]),
    ("@CurieuxDeNature",      "curieux-de-nature",        "Curieux de Nature",           ["sciences","nature"]),
    ("@GoldenMoustache",      "golden-moustache",         "Golden Moustache",            ["humour","comedie"]),
    ("@LeVrai_Pore",          "le-vrai-pore",             "Le Vrai Pore",                ["humour","gaming"]),
    ("@Antlion",              "antlion",                  "Antlion",                     ["cinema","critique"]),
    ("@laboiteimages",        "la-boite-images",          "La Boite Images",             ["cinema","culture"]),
    ("@MisterJDay",           "mister-jday",              "MisterJDay",                  ["gaming","culture geek"]),
    ("@FibreTigre",           "fibre-tigre",              "FibreTigre",                  ["gaming","jeux de role"]),
    ("@Nexus6",               "nexus6",                   "Nexus6",                      ["gaming"]),
    ("@ScienceInfuse",        "science-infuse",           "Science Infuse",              ["sciences","vulgarisation"]),
    ("@Micka_Breizh",         "micka-breizh",             "Micka Breizh",                ["gaming","culture geek"]),
    ("@quellehistoire_podcast","quelle-histoire",         "Quelle Histoire",             ["histoire","enfants","education"]),
    ("@LaTerreBleue",         "la-terre-bleue",           "La Terre Bleue",              ["sciences","environnement"]),
    ("@monsieurphi",          "monsieur-phi",             "Monsieur Phi",                ["philosophie","sciences"]),
    ("@Spe_spe",              "spe-spe",                  "Spe Spe",                     ["sciences","education"]),
    ("@GauthierThullen",      "gauthier-thullen",         "Gauthier Thullen",            ["histoire","culture"]),
    ("@HistoireParis",        "histoire-paris",           "Histoire de Paris",           ["histoire","culture"]),
    ("@MissClick",            "miss-click",               "Miss Click",                  ["gaming","culture geek"]),
    ("@LamissaThiam",         "lamissa",                  "Lamissa",                     ["societe","culture"]),
    ("@LeDesordreDesChoses",  "le-desordre-des-choses",  "Le Desordre des Choses",      ["societe","culture"]),
    ("@CharlieBocheux",       "charlie-bocheux",          "Charlie Bocheux",             ["humour","societe"]),
    ("@Psykocouac",           "psykocouac",               "Psykocouac",                  ["politique","societe"]),
    ("@HistoireSociale",      "histoire-sociale",         "Histoire Sociale",            ["histoire","societe"]),
    ("@EmilikoLemon",         "emiliko-lemon",            "Emiliko Lemon",               ["gaming","jeux inde"]),
    ("@TinkerHome",           "tinker-home",              "Tinker Home",                 ["DIY","maison"]),
    ("@Amixem",               "amixem",                   "Amixem",                      ["humour","vlogs"]),
    ("@PatateMolleProd",      "patate-molle",             "Patate Molle",                ["humour","gaming"]),
    ("@BenchmarkReviews",     "benchmark-reviews",        "Benchmark Reviews FR",        ["tech","numerique"]),
    ("@LiNuXFr",              "linux-fr",                 "LinuxFr",                     ["tech","numerique"]),
    ("@HardwareFR",           "hardware-fr",              "HardwareFR",                  ["tech","numerique"]),
    ("@TopAchat",             "top-achat",                "TopAchat",                    ["tech","numerique"]),
    ("@cestquoidemaindoc",    "cest-quoi-demain",         "C'est quoi demain?",         ["environnement","societe"]),
    ("@Suricate",             "suricate",                 "Suricate",                    ["humour","comedie"]),
    ("@WandaProductions",     "wanda-productions",        "Wanda Productions",           ["humour","comedie"]),
    ("@RoflCopter2110",       "roflcopter",               "RoflCopter",                  ["gaming","humour"]),
    ("@XiaoMaNiuFan",         "xiao-ma-niu",              "Xiao Ma Niu",                 ["culture","international"]),
    ("@ChefSimon",            "chef-simon",               "Chef Simon",                  ["gastronomie","cuisine"]),
    ("@SportVsChampions",     "sport-vs-champions",       "Sport vs Champions",          ["sport"]),
    ("@bde_france",           "bde-france",               "BDE France",                  ["societe","humour"]),
]

# --- Requetes iTunes ----------------------------------------------------------
ITUNES_QUERIES = [
    ("podcast histoire francais",           ["histoire"]),
    ("podcast true crime francais",         ["true crime", "societe"]),
    ("podcast tech numerique francais",     ["tech", "numerique"]),
    ("podcast gaming jeux video francais",  ["gaming"]),
    ("podcast cinema series francais",      ["cinema", "series"]),
    ("podcast sport running francais",      ["sport", "running"]),
    ("podcast football francais",           ["football", "sport"]),
    ("podcast economie business francais",  ["economie", "business"]),
    ("podcast bien etre psychologie",       ["bien-etre", "psychologie"]),
    ("podcast culture societe francais",    ["culture", "societe"]),
    ("podcast science vulgarisation",       ["sciences", "vulgarisation"]),
    ("podcast gastronomie cuisine",         ["gastronomie", "cuisine"]),
    ("podcast enfants education",           ["enfants", "education"]),
    ("podcast geopolitique international",  ["geopolitique", "international"]),
    ("podcast humour comedie francais",     ["humour", "comedie"]),
    ("podcast actualite news francais",     ["actualite", "news"]),
    ("podcast livres litterature",          ["livres", "culture"]),
    ("podcast sante medecine",              ["sante"]),
    ("podcast entrepreneuriat startup",     ["business", "entrepreneuriat"]),
    ("podcast musique culture",             ["musique", "culture"]),
    ("chaine youtube histoire francaise",   ["histoire"]),
    ("chaine youtube science vulgarisation",["sciences", "vulgarisation"]),
    ("chaine youtube gaming retrogaming",   ["gaming", "retro"]),
    ("chaine youtube cuisine gastronomie",  ["gastronomie", "cuisine"]),
    ("chaine youtube renovation bricolage", ["renovation", "DIY"]),
]

# --- Helpers ------------------------------------------------------------------
def slugify(text):
    text = text.lower()
    for src, dst in [("aaoaa","a"),("eeeeee","e"),("ii","i"),("oo","o"),("uuuu","u"),("c","c")]:
        pass  # simplified - real accents handled below
    import unicodedata
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]

def load_existing(slug):
    path = DATA_DIR / f"{slug}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f: return json.load(f)
    return None

def save_content(data):
    slug = data["slug"]
    path = DATA_DIR / f"{slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  + {slug}")

def today():
    from datetime import date
    return date.today().isoformat()

# --- Collecte iTunes ----------------------------------------------------------
def fetch_itunes(term, limit=200):
    url = "https://itunes.apple.com/search"
    params = {"term": term, "country": "fr", "media": "podcast", "limit": limit, "lang": "fr_fr"}
    try:
        return _http_get(url, params=params, timeout=15).get("results", [])
    except Exception as e:
        print(f"  ! iTunes error for '{term}': {e}")
        return []

def itunes_to_content(item, categories):
    name   = item.get("collectionName", "").strip()
    artist = item.get("artistName", "").strip()
    if not name: return None
    slug = slugify(name)
    if not slug: return None

    existing = load_existing(slug)
    if existing:
        if not existing.get("platforms", {}).get("apple"):
            existing.setdefault("platforms", {})["apple"] = {
                "url":         item.get("collectionViewUrl"),
                "trackId":     item.get("collectionId"),
                "rating":      item.get("averageUserRating"),
                "ratingCount": item.get("userRatingCount"),
                "episodeCount":item.get("trackCount"),
            }
            existing["updatedAt"] = today()
            save_content(existing)
        return existing

    return {
        "slug":        slug,
        "title":       name,
        "author":      artist,
        "type":        "podcast",
        "categories":  categories,
        "description": item.get("description") or item.get("shortDescription") or "",
        "image":       item.get("artworkUrl600") or item.get("artworkUrl100"),
        "language":    item.get("primaryGenreName", ""),
        "platforms": {
            "apple": {
                "url":         item.get("collectionViewUrl"),
                "trackId":     item.get("collectionId"),
                "rating":      item.get("averageUserRating"),
                "ratingCount": item.get("userRatingCount"),
                "episodeCount":item.get("trackCount"),
            }
        },
        "mediacritic": None,
        "tags":        categories,
        "updatedAt":   today(),
    }

# --- Collecte YouTube (API) ---------------------------------------------------
def fetch_youtube_channel(handle_or_id, api_key):
    if not api_key: return None
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "snippet,statistics", "forHandle": handle_or_id.lstrip("@"), "key": api_key}
    try:
        data = _http_get(url, params=params, timeout=15)
        items = data.get("items", [])
        if not items:
            params = {"part": "snippet,statistics", "id": handle_or_id, "key": api_key}
            data = _http_get(url, params=params, timeout=15)
            items = data.get("items", [])
        return items[0] if items else None
    except Exception as e:
        print(f"  ! YouTube API error for '{handle_or_id}': {e}")
        return None

def fetch_yt_oembed(handle):
    """Fetch thumbnail/title via YouTube oEmbed (no API key needed)."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/{handle}&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return None

# --- Collecte YouTube catalogue cure -----------------------------------------
def collect_youtube_catalog(api_key=None):
    print("\n-- Catalogue YouTube --")
    added = 0
    skipped = 0
    for handle, slug, title, categories in YOUTUBE_CHANNELS:
        existing = load_existing(slug)
        if existing and existing.get("type") == "youtube":
            skipped += 1
            continue

        data = existing or {
            "slug":        slug,
            "title":       title,
            "author":      title,
            "type":        "youtube",
            "categories":  categories,
            "description": "",
            "image":       None,
            "language":    "fr",
            "platforms":   {"youtube": {"url": f"https://www.youtube.com/{handle}"}},
            "mediacritic": None,
            "tags":        categories,
            "updatedAt":   today(),
        }

        if api_key:
            ch = fetch_youtube_channel(handle, api_key)
            if ch:
                sn = ch.get("snippet", {})
                st = ch.get("statistics", {})
                data["description"] = sn.get("description", "")
                data["image"] = sn.get("thumbnails", {}).get("high", {}).get("url")
                data.setdefault("platforms", {})["youtube"] = {
                    "url":         f"https://www.youtube.com/{handle}",
                    "channelId":   ch["id"],
                    "subscribers": int(st.get("subscriberCount", 0)),
                    "totalViews":  int(st.get("viewCount", 0)),
                    "videoCount":  int(st.get("videoCount", 0)),
                }
                data["updatedAt"] = today()
                save_content(data)
                added += 1
                continue

        if not data.get("image"):
            oembed = fetch_yt_oembed(handle)
            if oembed:
                data["image"] = oembed.get("thumbnail_url")
                if not data.get("title") or data["title"] == slug:
                    data["title"] = oembed.get("author_name", title)

        data["updatedAt"] = today()
        save_content(data)
        added += 1
        time.sleep(0.2)

    print(f"  YouTube: {added} ajoutees, {skipped} deja presentes")

# --- Collecte Spotify (optionnel) ---------------------------------------------
def get_spotify_token(client_id, client_secret):
    if not client_id or not client_secret: return None
    try:
        import base64
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=b"grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("access_token")
    except Exception:
        return None

def fetch_spotify_show(show_id, token):
    if not token or not show_id: return None
    try:
        req = urllib.request.Request(
            f"https://api.spotify.com/v1/shows/{show_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return None

# --- Construction des fiches MediaCritic -------------------------------------
def build_mediacritic_entries(youtube_key=None, spotify_token=None):
    print("\n-- Episodes MediaCritic --")
    for ep in MEDIACRITIC_EPISODES:
        slug = ep["slug"]
        existing = load_existing(slug)
        data = existing or {
            "slug":        slug,
            "title":       ep["title"],
            "author":      "MediaCritic",
            "type":        ep["type"],
            "categories":  ep["categories"],
            "description": "",
            "image":       None,
            "language":    "fr",
            "platforms":   {},
            "mediacritic": {
                "episodeNumber": ep["ep"],
                "episodeSlug":   slug,
                "analyseUrl":    f"/episodes/{slug}.html",
            },
            "tags":      ep["categories"],
            "updatedAt": today(),
        }

        if ep.get("spotify_show") and spotify_token:
            show = fetch_spotify_show(ep["spotify_show"], spotify_token)
            if show:
                data.setdefault("platforms", {})["spotify"] = {
                    "url":          f"https://open.spotify.com/show/{ep['spotify_show']}",
                    "showId":       ep["spotify_show"],
                    "followers":    show.get("followers", {}).get("total"),
                    "episodeCount": show.get("total_episodes"),
                    "description":  show.get("description"),
                }
                if not data.get("image"):
                    images = show.get("images", [])
                    data["image"] = images[0]["url"] if images else None
                if not data.get("description"):
                    data["description"] = show.get("description", "")

        if ep.get("youtube") and youtube_key:
            ch = fetch_youtube_channel(ep["youtube"], youtube_key)
            if ch:
                sn = ch.get("snippet", {})
                st = ch.get("statistics", {})
                data.setdefault("platforms", {})["youtube"] = {
                    "url":         f"https://www.youtube.com/{ep['youtube']}",
                    "channelId":   ch["id"],
                    "subscribers": int(st.get("subscriberCount", 0)),
                    "totalViews":  int(st.get("viewCount", 0)),
                    "videoCount":  int(st.get("videoCount", 0)),
                }
                if not data.get("image"):
                    data["image"] = sn.get("thumbnails", {}).get("high", {}).get("url")
                if not data.get("description"):
                    data["description"] = sn.get("description", "")

        data["updatedAt"] = today()
        save_content(data)

# --- Collecte iTunes en masse ------------------------------------------------
def collect_itunes_catalog():
    print("\n-- Catalogue iTunes --")
    seen_slugs = set()
    total = 0
    for term, cats in ITUNES_QUERIES:
        print(f"  -> {term}")
        results = fetch_itunes(term, limit=200)
        new = 0
        for item in results:
            data = itunes_to_content(item, cats)
            if not data: continue
            if data["slug"] in seen_slugs: continue
            seen_slugs.add(data["slug"])
            existing = load_existing(data["slug"])
            if existing and existing.get("mediacritic"): continue
            save_content(data)
            new += 1
        total += new
        print(f"     {new} nouvelles fiches ({len(results)} resultats iTunes)")
        time.sleep(0.5)
    print(f"\n  Total nouvelles fiches : {total}")

# --- Scraping notes Apple Podcasts -------------------------------------------
def fetch_apple_rating_page(track_id):
    """Scrape Apple Podcasts page to get aggregate rating and review count."""
    url = f"https://podcasts.apple.com/fr/podcast/id{track_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }
    try:
        r = _requests_lib.get(url, headers=headers, timeout=12) if _requests_lib else None
        if r is None:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
        else:
            r.raise_for_status()
            text = r.text
        m = re.search(r'"ratingValue":([0-9.]+),"reviewCount":([0-9]+)', text)
        if m:
            rv = float(m.group(1))
            rc = int(m.group(2))
            return rv if rv > 0 else None, rc if rc > 0 else None
    except Exception:
        pass
    return None, None

def update_ratings_missing():
    """Fetch Apple Podcasts ratings for entries that have trackId but no rating."""
    print("
-- Mise a jour des notes Apple Podcasts --")
    needs_update = []
    for path in DATA_DIR.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        apple = d.get("platforms", {}).get("apple", {})
        tid = apple.get("trackId")
        if tid and apple.get("rating") is None:
            needs_update.append((path, d, tid))

    if not needs_update:
        print("  Toutes les notes sont deja renseignees.")
        return

    print(f"  {len(needs_update)} fiches sans note a recuperer...")
    updated = 0

    def _fetch(args):
        path, d, tid = args
        rating, count = fetch_apple_rating_page(tid)
        return path, d, rating, count

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(_fetch, args) for args in needs_update]
        for fut in as_completed(futures):
            path, d, rating, count = fut.result()
            if rating is not None:
                d["platforms"]["apple"]["rating"] = rating
                d["platforms"]["apple"]["ratingCount"] = count
                save_content(d)
                updated += 1

    print(f"  Notes mises a jour : {updated}/{len(needs_update)}")

# --- Generation du catalog.json ----------------------------------------------
def generate_catalog():
    print("\n-- Generation catalog.json --")
    catalog = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        catalog.append({
            "slug":          d.get("slug"),
            "title":         d.get("title"),
            "author":        d.get("author", ""),
            "type":          d.get("type"),
            "categories":    d.get("categories", []),
            "tags":          d.get("tags", []),
            "image":         d.get("image"),
            "description":   (d.get("description") or "")[:200],
            "hasMediacritic":bool(d.get("mediacritic")),
            "mcEpisode":     d.get("mediacritic", {}).get("episodeNumber") if d.get("mediacritic") else None,
            "rating":        d.get("platforms", {}).get("apple", {}).get("rating"),
            "ratingCount":   d.get("platforms", {}).get("apple", {}).get("ratingCount"),
        })

    with open(CATALOG_OUT, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  {len(catalog)} entrees -> data/catalog.json ({CATALOG_OUT.stat().st_size // 1024} KB)")

# --- Main --------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",           choices=["podcast", "youtube", "all"], default="all")
    parser.add_argument("--youtube-key",    default=os.getenv("YOUTUBE_API_KEY"))
    parser.add_argument("--spotify-id",     default=os.getenv("SPOTIFY_CLIENT_ID"))
    parser.add_argument("--spotify-secret", default=os.getenv("SPOTIFY_CLIENT_SECRET"))
    args = parser.parse_args()

    spotify_token = get_spotify_token(args.spotify_id, args.spotify_secret)
    if spotify_token: print("Spotify connecte")
    if args.youtube_key: print("YouTube connecte")

    build_mediacritic_entries(args.youtube_key, spotify_token)

    if args.mode in ("podcast", "all"):
        collect_itunes_catalog()

    if args.mode in ("youtube", "all"):
        collect_youtube_catalog(args.youtube_key)

    update_ratings_missing()

    generate_catalog()
    print("\nTermine.")
