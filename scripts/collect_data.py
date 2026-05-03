#!/usr/bin/env python3
"""
MediaCritic — Collecte de données catalogue
Sources : iTunes Search API (gratuit), YouTube Data API v3, Spotify API
Usage   : python collect_data.py [--youtube-key KEY] [--spotify-id ID --spotify-secret SECRET]
"""

import json, os, re, time, hashlib, requests, argparse
from pathlib import Path

# ─── Chemins ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent / "site"
DATA_DIR    = ROOT / "data" / "content"
CATALOG_OUT = ROOT / "data" / "catalog.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Épisodes MediaCritic existants ───────────────────────────────────────────
MEDIACRITIC_EPISODES = [
    {"ep": 1,  "slug": "la-5e-de-couv",              "title": "La 5e de Couv'",           "type": "podcast", "categories": ["livres","culture"],          "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 2,  "slug": "lesprit-critique",            "title": "L'Esprit Critique",        "type": "podcast", "categories": ["sciences","société"],         "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 3,  "slug": "hardisk-stories",             "title": "Hardisk Stories",          "type": "podcast", "categories": ["tech","geek"],                "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 4,  "slug": "le-podcast-du-weekend",       "title": "Le Podcast du Weekend",    "type": "podcast", "categories": ["culture","actualité"],        "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 5,  "slug": "braincast",                   "title": "BrainCast",                "type": "podcast", "categories": ["sciences","vulgarisation"],   "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 6,  "slug": "floodcast",                   "title": "Floodcast",                "type": "podcast", "categories": ["gaming","culture geek"],      "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 7,  "slug": "fin-du-game",                 "title": "Fin du Game",              "type": "podcast", "categories": ["gaming"],                     "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 8,  "slug": "blockbusters",                "title": "BlockBusters",             "type": "podcast", "categories": ["cinéma","séries"],            "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 9,  "slug": "la-story-des-echos",          "title": "La Story des Échos",       "type": "podcast", "categories": ["économie","business"],        "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 10, "slug": "le-rendez-vous-tech",         "title": "Le Rendez-vous Tech",      "type": "podcast", "categories": ["tech","numérique"],           "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 11, "slug": "emotions",                    "title": "Émotions",                 "type": "podcast", "categories": ["bien-être","psychologie"],    "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 12, "slug": "safepace",                    "title": "SafePace",                 "type": "podcast", "categories": ["sport","running","endurance"], "itunes_id": None, "spotify_show": "7AH8nT1CoTmV1MfhxyTl3n", "youtube": None},
    {"ep": 13, "slug": "entrez-dans-lhistoire",       "title": "Entrez dans l'Histoire",   "type": "podcast", "categories": ["histoire"],                   "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 14, "slug": "seldell",                     "title": "Seldell",                  "type": "youtube", "categories": ["gaming","jeux indé"],          "itunes_id": None, "spotify_show": None, "youtube": "@seldell"},
    {"ep": 15, "slug": "passion-renovation",          "title": "Passion Rénovation",       "type": "youtube", "categories": ["rénovation","DIY","maison"],  "itunes_id": None, "spotify_show": None, "youtube": "@passionrenovation"},
    {"ep": 16, "slug": "chef-otaku",                  "title": "Chef Otaku",               "type": "youtube", "categories": ["cuisine","anime","culture"],  "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 17, "slug": "lheure-du-crime",             "title": "L'Heure du Crime",         "type": "podcast", "categories": ["true crime","société"],       "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 18, "slug": "on-va-deguster",              "title": "On va déguster",           "type": "podcast", "categories": ["gastronomie","cuisine"],      "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 19, "slug": "silicon-carne",               "title": "Silicon Carne",            "type": "podcast", "categories": ["tech","humour"],              "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 20, "slug": "extraterrien",                "title": "Extraterrien",             "type": "podcast", "categories": ["sport","société"],            "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 21, "slug": "lafter-foot",                 "title": "L'After Foot",             "type": "podcast", "categories": ["football","sport"],           "itunes_id": None, "spotify_show": None, "youtube": None},
    {"ep": 22, "slug": "notabene",                    "title": "NotaBene",                 "type": "youtube", "categories": ["histoire","géopolitique"],    "itunes_id": None, "spotify_show": None, "youtube": "@nota.bene"},
    {"ep": 23, "slug": "re-take",                     "title": "Re-Take",                  "type": "youtube", "categories": ["gaming","critique"],          "itunes_id": None, "spotify_show": None, "youtube": "@Retake"},
    {"ep": 24, "slug": "cest-plus-complique-que-ca",  "title": "C'est plus compliqué que ça","type": "podcast","categories": ["histoire","société"],        "itunes_id": None, "spotify_show": "1pvsIBHWTfk9aROklANap8", "youtube": None},
    {"ep": 25, "slug": "le-joueur-du-grenier",        "title": "Le Joueur du Grenier",     "type": "youtube", "categories": ["gaming","rétro","nostalgie"], "itunes_id": None, "spotify_show": None, "youtube": "@joueurdugrenier"},
    {"ep": 26, "slug": "quelle-histoire",             "title": "Quelle Histoire",          "type": "podcast", "categories": ["histoire","enfants","éducation"],"itunes_id": None, "spotify_show": "76IarJo3W3YmD3e9V43wD0", "youtube": "@quellehistoire_podcast"},
]

# ─── Requêtes iTunes par catégorie ────────────────────────────────────────────
ITUNES_QUERIES = [
    # (terme de recherche, catégories internes)
    ("podcast histoire francais",           ["histoire"]),
    ("podcast true crime français",         ["true crime", "société"]),
    ("podcast tech numérique français",     ["tech", "numérique"]),
    ("podcast gaming jeux video français",  ["gaming"]),
    ("podcast cinema series français",      ["cinéma", "séries"]),
    ("podcast sport running français",      ["sport", "running"]),
    ("podcast football français",           ["football", "sport"]),
    ("podcast économie business français",  ["économie", "business"]),
    ("podcast bien etre psychologie",       ["bien-être", "psychologie"]),
    ("podcast culture société français",    ["culture", "société"]),
    ("podcast science vulgarisation",       ["sciences", "vulgarisation"]),
    ("podcast gastronomie cuisine",         ["gastronomie", "cuisine"]),
    ("podcast enfants éducation",           ["enfants", "éducation"]),
    ("podcast geopolitique international",  ["géopolitique", "international"]),
    ("podcast humour comédie français",     ["humour", "comédie"]),
    ("podcast actualité news français",     ["actualité", "news"]),
    ("podcast livres littérature",          ["livres", "culture"]),
    ("podcast santé médecine",              ["santé"]),
    ("podcast entrepreneuriat startup",     ["business", "entrepreneuriat"]),
    ("podcast musique culture",             ["musique", "culture"]),
    ("chaîne youtube histoire française",   ["histoire"]),
    ("chaîne youtube science vulgarisation",["sciences", "vulgarisation"]),
    ("chaîne youtube gaming retrogaming",   ["gaming", "rétro"]),
    ("chaîne youtube cuisine gastronomie",  ["gastronomie", "cuisine"]),
    ("chaîne youtube renovation bricolage", ["rénovation", "DIY"]),
]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def slugify(text):
    text = text.lower()
    text = re.sub(r"[àâä]", "a", text); text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[îï]", "i", text);  text = re.sub(r"[ôö]", "o", text)
    text = re.sub(r"[ùûü]", "u", text); text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]

def load_existing(slug):
    path = DATA_DIR / f"{slug}.json"
    if path.exists():
        with open(path) as f: return json.load(f)
    return None

def save_content(data):
    slug = data["slug"]
    path = DATA_DIR / f"{slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {slug}")

def today():
    from datetime import date
    return date.today().isoformat()

# ─── Collecte iTunes ──────────────────────────────────────────────────────────
def fetch_itunes(term, limit=200):
    url = "https://itunes.apple.com/search"
    params = {"term": term, "country": "fr", "media": "podcast", "limit": limit, "lang": "fr_fr"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as e:
        print(f"  ⚠ iTunes error for '{term}': {e}")
        return []

def itunes_to_content(item, categories):
    name   = item.get("collectionName", "").strip()
    artist = item.get("artistName", "").strip()
    if not name: return None
    slug = slugify(name)
    if not slug: return None

    existing = load_existing(slug)
    if existing:
        # Enrich without overwriting
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

# ─── Collecte YouTube (optionnel, nécessite une clé API) ─────────────────────
def fetch_youtube_channel(handle_or_id, api_key):
    if not api_key: return None
    url = "https://www.googleapis.com/youtube/v3/channels"
    # Essaie par handle d'abord
    params = {"part": "snippet,statistics", "forHandle": handle_or_id.lstrip("@"), "key": api_key}
    try:
        r = requests.get(url, params=params, timeout=15)
        items = r.json().get("items", [])
        if not items:  # Fallback par ID
            params = {"part": "snippet,statistics", "id": handle_or_id, "key": api_key}
            r = requests.get(url, params=params, timeout=15)
            items = r.json().get("items", [])
        return items[0] if items else None
    except Exception as e:
        print(f"  ⚠ YouTube error for '{handle_or_id}': {e}")
        return None

# ─── Collecte Spotify (optionnel) ─────────────────────────────────────────────
def get_spotify_token(client_id, client_secret):
    if not client_id or not client_secret: return None
    try:
        r = requests.post("https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret), timeout=10)
        return r.json().get("access_token")
    except: return None

def fetch_spotify_show(show_id, token):
    if not token or not show_id: return None
    try:
        r = requests.get(f"https://api.spotify.com/v1/shows/{show_id}",
            headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return r.json() if r.ok else None
    except: return None

# ─── Construction des fiches MediaCritic ─────────────────────────────────────
def build_mediacritic_entries(youtube_key=None, spotify_token=None):
    print("\n── Épisodes MediaCritic ──")
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

        # Spotify
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

        # YouTube
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

# ─── Collecte iTunes en masse ─────────────────────────────────────────────────
def collect_itunes_catalog():
    print("\n── Catalogue iTunes ──")
    seen_slugs = set()
    total = 0
    for term, cats in ITUNES_QUERIES:
        print(f"  → {term}")
        results = fetch_itunes(term, limit=200)
        new = 0
        for item in results:
            data = itunes_to_content(item, cats)
            if not data: continue
            if data["slug"] in seen_slugs: continue
            seen_slugs.add(data["slug"])
            # Ne pas écraser les fiches MediaCritic
            existing = load_existing(data["slug"])
            if existing and existing.get("mediacritic"): continue
            save_content(data)
            new += 1
        total += new
        print(f"     {new} nouvelles fiches ({len(results)} résultats iTunes)")
        time.sleep(0.5)  # Respecte le rate limit iTunes
    print(f"\n  Total nouvelles fiches : {total}")

# ─── Génération du catalog.json (index léger) ─────────────────────────────────
def generate_catalog():
    print("\n── Génération catalog.json ──")
    catalog = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        # Version allégée pour la recherche client
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
    print(f"  {len(catalog)} entrées → data/catalog.json ({CATALOG_OUT.stat().st_size // 1024} KB)")

# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--youtube-key",      default=os.getenv("YOUTUBE_API_KEY"))
    parser.add_argument("--spotify-id",       default=os.getenv("SPOTIFY_CLIENT_ID"))
    parser.add_argument("--spotify-secret",   default=os.getenv("SPOTIFY_CLIENT_SECRET"))
    parser.add_argument("--skip-itunes",      action="store_true")
    parser.add_argument("--skip-mediacritic", action="store_true")
    args = parser.parse_args()

    spotify_token = get_spotify_token(args.spotify_id, args.spotify_secret)
    if spotify_token: print("✓ Spotify connecté")
    if args.youtube_key: print("✓ YouTube connecté")

    if not args.skip_mediacritic:
        build_mediacritic_entries(args.youtube_key, spotify_token)
    if not args.skip_itunes:
        collect_itunes_catalog()

    generate_catalog()
    print("\n✅ Terminé.")
