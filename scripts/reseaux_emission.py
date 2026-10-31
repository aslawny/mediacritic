# -*- coding: utf-8 -*-
"""
Comptes de reseaux sociaux de l'emission du jour, pour la taguer dans le kit
(demande de l'utilisateur, 31/10/2026 : « sans cela l'interet est limite »).

SOURCES OFFICIELLES UNIQUEMENT, jamais de compte devine :
  1. chaine YouTube : la page « A propos » (liens que la chaine affiche) ;
  2. podcast : l'en-tete du flux RSS (pas les episodes : ce sont des invites),
     puis la page d'accueil du site officiel indique par le flux ;
  3. la description de la fiche.
Les liens courts (bit.ly, on.fb.me…) sont deplies. Les comptes des
hebergeurs (Ausha, Acast…) et de MediaCritic sont ecartes.

Retour : {reseau: [{"compte", "url", "source"}]} — reseau parmi instagram, x,
tiktok, facebook, linkedin, youtube, threads, bluesky, twitch.
"""
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept-Language": "fr-FR",
      "Cookie": "SOCS=CAESEwgDEgk4NjM5OTEzODIaAmZyIAEaBgiA4P-oBg; CONSENT=YES+cb"}

MOTIFS = {
    "instagram": r"instagram\.com/([A-Za-z0-9_.]{2,30})",
    "x": r"(?:twitter|x)\.com/(?:#!/)?@?([A-Za-z0-9_]{2,15})",
    "tiktok": r"tiktok\.com/@([A-Za-z0-9_.]{2,24})",
    "facebook": r"(?:facebook|fb)\.com/([A-Za-z0-9.\-]{2,50})",
    "linkedin": r"linkedin\.com/((?:company|in|school)/[A-Za-z0-9\-_%]{2,80})",
    "youtube": r"youtube\.com/(@[A-Za-z0-9_.\-]{2,30})",
    "threads": r"threads\.(?:net|com)/@([A-Za-z0-9_.]{2,30})",
    "bluesky": r"bsky\.app/profile/([A-Za-z0-9.\-]{3,60})",
    "twitch": r"twitch\.tv/([A-Za-z0-9_]{3,25})",
}
URLS = {
    "instagram": "https://www.instagram.com/{}/", "x": "https://x.com/{}",
    "tiktok": "https://www.tiktok.com/@{}", "facebook": "https://www.facebook.com/{}",
    "linkedin": "https://www.linkedin.com/{}", "youtube": "https://www.youtube.com/{}",
    "threads": "https://www.threads.net/@{}", "bluesky": "https://bsky.app/profile/{}",
    "twitch": "https://www.twitch.tv/{}",
}
# Chemins qui ne sont pas des comptes, comptes d'hebergeurs et de MediaCritic.
EXCLUS = {
    "share", "sharer", "sharer.php", "intent", "home", "p", "reel", "reels", "explore",
    "hashtag", "watch", "embed", "plugins", "tr", "dialog", "policies", "legal", "help",
    "about", "login", "signup", "search", "i", "privacy", "terms", "groups", "events",
    "pages", "profile.php", "people", "feed", "channel", "c", "user", "results", "stories",
    "ausha", "ausha.co", "acast", "acastfr", "audion", "audionfm", "spotify", "spotifyfr",
    "applepodcasts", "deezer", "podcloud", "soundcloud", "anchor", "smartlink", "linktree",
    "mediacriticinc", "mediacritic.inc", "mediacritic", "youtube", "tiktok", "instagram",
    "twitter", "facebook", "x", "audiomeans", "orsonmedia", "podcastics",
    "youtubefr", "teamyoutube", "youtubecreators", "youtubemusic", "youtubegaming",
}
COURTS = re.compile(r"https?://(?:bit\.ly|on\.fb\.me|goo\.gl|tinyurl\.com|ow\.ly|t\.co|lnkd\.in|"
                    r"linktr\.ee|smarturl\.it)/[^\s\"'<>)&]+", re.I)
HEBERGEURS = re.compile(r"soundcloud|spotify|apple\.com|deezer|youtube\.com|youtu\.be|"
                        r"feeds\.|feed\.|rss\.|podcast\.ausha|ausha\.co|audiomeans|acast\.com/public", re.I)


def _lire(url, n=2_500_000, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(n).decode("utf-8", "replace")


def _deplier(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.geturl()
    except Exception:
        return ""


def _extraire(texte, source, out):
    texte = urllib.parse.unquote(texte.replace("\\/", "/"))
    for reseau, motif in MOTIFS.items():
        for m in re.findall(motif, texte, re.I):
            compte = m.strip("/.").split("?")[0]
            if not compte or compte.lower() in EXCLUS:
                continue
            liste = out.setdefault(reseau, [])
            if compte.lower() not in {c["compte"].lower() for c in liste}:
                liste.append({"compte": compte, "url": URLS[reseau].format(compte), "source": source})


def _youtube(cid, out):
    x = _lire(f"https://www.youtube.com/channel/{cid}/about")
    liens = [urllib.parse.unquote(m) for m in re.findall(r"q=(https?%3A%2F%2F[^\"&\\]+)", x)]
    liens += re.findall(r'"content":"((?:www\.)?[a-z]+\.[a-z.]+/[^"]+)"', x)
    liens += re.findall(r'"(https?://(?:www\.)?(?:instagram|tiktok|twitter|x|facebook|twitch|linkedin|'
                        r'threads|bsky)\.[a-z]+/[^"]+)"', x)
    for c in [l for l in liens if COURTS.match(l)][:8]:
        liens.append(_deplier(c))
    _extraire(" ".join(liens), "chaîne YouTube", out)


def _podcast(slug, out):
    feeds_p = ROOT / "data" / "_feed_urls.json"
    feeds = json.loads(feeds_p.read_text(encoding="utf-8")) if feeds_p.exists() else {}
    flux = feeds.get(slug)
    if not flux:
        return
    tete = _lire(flux, 200_000).split("<item", 1)[0]
    for c in COURTS.findall(tete)[:6]:
        tete += " " + _deplier(c)
    _extraire(tete, "flux du podcast", out)
    site = re.search(r"<link>\s*(https?://[^<\s]+)\s*</link>", tete)
    if site and not HEBERGEURS.search(site.group(1)):
        try:
            page = _lire(site.group(1), 800_000)
            _extraire(page, "site officiel", out)
        except Exception:
            pass


def reseaux(slug, type_):
    out = {}
    p = ROOT / "data" / "content" / f"{slug}.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    try:
        cid = (d.get("platforms", {}).get("youtube") or {}).get("channelId")
        if type_ == "youtube" and cid:
            _youtube(cid, out)
        else:
            _podcast(slug, out)
    except Exception as e:
        print(f"  ! réseaux de {slug} : {e}")
    _extraire(d.get("description") or "", "description", out)
    # Ordre d'affichage stable, 4 comptes au plus par reseau.
    return {r: out[r][:4] for r in MOTIFS if out.get(r)}
