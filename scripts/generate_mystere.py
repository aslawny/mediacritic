#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
« Le Mystere du Jour » (lancement le lundi 23/11/2026) : deviner le podcast du
jour en 6 indices maximum, facon Wordle.

UNE SEULE SOURCE : data/du_jour.json, ecrit chaque matin par du_jour.py. Ce
script n'invente rien : il DERIVE de chaque podcast du jour
  - data/mystere.json : un mystere par date (indices + revelation), encode
    (base64 ; la reponse n'y figure que sous forme d'empreinte) ;
  - mystere.html : la page (/mystere), chartee, indexable.

Donnees que du_jour.json ne porte pas, calculees UNE fois par date et gardees
dans data/_mystere_cache.json (fichier « _ » : jamais publie par Jekyll) :
  - annee de creation : 1er episode du flux RSS (podcast), « Actif depuis »
    de la page YouTube (chaine) ;
  - duree moyenne : <itunes:duration> du flux, ou durees de la page videos ;
  - lecteur officiel : YouTube (nocookie) pour une chaine ; pour un podcast,
    Spotify si l'emission est connue chez Spotify, sinon Apple (episode
    retrouve par son titre, sinon l'emission entiere).
Corrections a la main, facultatives : manifests/mystere-corrections.json
({date: {champ: valeur}}), lu en dernier, prioritaire. Voir
scripts/README-mystere.md.

Reseau : urllib, puis curl en secours (le Python de la machine locale echoue
sur les certificats HTTPS ; chez GitHub, urllib suffit).

Usage : python scripts/generate_mystere.py [--sans-reseau]
"""
import argparse
import base64
import io
import json
import re
import statistics
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charte import appliquer as charte_appliquer, MARQUEUR_LECTEURS  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"
LANCEMENT = date(2026, 11, 23)          # mystere n°1
FENETRE_JOURS = 40                      # mysteres gardes dans mystere.json
CACHE = DATA / "_mystere_cache.json"
CORRECTIONS = ROOT / "manifests" / "mystere-corrections.json"
UA = "Mozilla/5.0 (compatible; MediaCriticBot/1.0)"
YT_COOKIE = "SOCS=CAESEwgDEgk4NjM5OTEzODIaAmZyIAEaBgiA4P-oBg; CONSENT=YES+cb"


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------
def h(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def normaliser(s):
    """Comparaison des reponses : sans accents, sans casse, sans ponctuation.
    DOIT rester identique a normaliser() de assets/mystere.js."""
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " et ")
    return re.sub(r"[^a-z0-9]+", "", s)


def empreinte(s):
    """cyrb53 : empreinte 53 bits. DOIT rester identique a empreinte() de
    assets/mystere.js (meme algorithme, meme graine). Pas de cryptographie :
    l'anti-triche demande est volontairement leger."""
    h1, h2 = 0xDEADBEEF ^ 0x4D43, 0x41C6CE57 ^ 0x4D43
    for ch in s:
        c = ord(ch)
        h1 = ((h1 ^ c) * 2654435761) & 0xFFFFFFFF
        h2 = ((h2 ^ c) * 1597334677) & 0xFFFFFFFF
    h1 = ((h1 ^ (h1 >> 16)) * 2246822507) & 0xFFFFFFFF
    h1 ^= ((h2 ^ (h2 >> 13)) * 3266489909) & 0xFFFFFFFF
    h2 = ((h2 ^ (h2 >> 16)) * 2246822507) & 0xFFFFFFFF
    h2 ^= ((h1 ^ (h1 >> 13)) * 3266489909) & 0xFFFFFFFF
    return format(4294967296 * (2097151 & h2) + (h1 & 0xFFFFFFFF), "x")


def lire(url, octets=None, cookie=None):
    """Texte d'une URL : urllib, sinon curl. '' si les deux echouent."""
    entetes = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}
    if cookie:
        entetes["Cookie"] = cookie
    try:
        req = urllib.request.Request(url, headers=entetes)
        with urllib.request.urlopen(req, timeout=25) as r:
            brut = r.read(octets) if octets else r.read()
        if brut[:2] == b"\x1f\x8b":
            import zlib
            brut = zlib.decompressobj(31).decompress(brut, 20 * 1024 * 1024)
        return brut.decode("utf-8", "replace")
    except Exception:
        pass
    try:
        cmd = ["curl", "-sL", "--compressed", "-m", "30", "-A", UA,
               "-H", "Accept-Language: fr-FR,fr;q=0.9"]
        if cookie:
            cmd += ["-H", "Cookie: " + cookie]
        r = subprocess.run(cmd + [url], capture_output=True, timeout=40)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def minutes(duree):
    """'01:03:01' | '55:23' | '3781' -> minutes (float) ou None."""
    d = (duree or "").strip()
    try:
        if ":" in d:
            p = [int(x) for x in d.split(":")]
            sec = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
        else:
            sec = int(float(d))
        return sec / 60 if sec > 0 else None
    except Exception:
        return None


def fiche(slug):
    p = DATA / "content" / f"{slug}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


# --------------------------------------------------------------------------
# Donnees calculees une fois par date (cache)
# --------------------------------------------------------------------------
def infos_podcast(c, f):
    pf = f.get("platforms") or {}
    tid = (pf.get("apple") or {}).get("trackId")
    out = {}
    feeds = {}
    try:
        feeds = json.loads((DATA / "_feed_urls.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    feed = feeds.get(c["slug"])
    if not feed and tid:
        try:
            r = json.loads(lire(f"https://itunes.apple.com/lookup?id={tid}&country=fr") or "{}")
            feed = (r.get("results") or [{}])[0].get("feedUrl")
        except Exception:
            feed = None
    if feed:
        x = lire(feed)
        dates = []
        for d in re.findall(r"<pubDate>(.*?)</pubDate>", x):
            try:
                from email.utils import parsedate_to_datetime
                dates.append(parsedate_to_datetime(d.strip()))
            except Exception:
                pass
        if dates:
            out["annee"] = min(dates).year
            # Flux tronque (RMC, Radio France : les ~100 derniers episodes) :
            # le plus ancien episode n'est pas le premier. On ne garde qu'un
            # plancher (« depuis au moins »), jamais une fausse date.
            if len(dates) >= 95:
                out["annee_min"] = True
        durees = [m for m in (minutes(v) for v in re.findall(
            r"<itunes:duration>(.*?)</itunes:duration>", x)[:12]) if m]
        if durees:
            out["duree_min"] = round(statistics.median(durees))
    # Lecteur : Spotify si l'emission y est connue, sinon Apple.
    sp = (pf.get("spotify") or {}).get("showId")
    if sp:
        out["lecteur"] = {"type": "spotify", "src": f"https://open.spotify.com/embed/show/{sp}"}
    elif tid:
        src = f"https://embed.podcasts.apple.com/fr/podcast/id{tid}?theme=dark"
        titre_ep = normaliser((c.get("episode") or {}).get("titre"))
        if titre_ep:
            try:
                r = json.loads(lire(f"https://itunes.apple.com/lookup?id={tid}&country=fr"
                                    "&entity=podcastEpisode&limit=60") or "{}")
                for e in r.get("results") or []:
                    t = normaliser(e.get("trackName"))
                    if e.get("wrapperType") == "podcastEpisode" and t and (
                            t == titre_ep or t.startswith(titre_ep[:40]) or titre_ep.startswith(t[:40])):
                        src = (f"https://embed.podcasts.apple.com/fr/podcast/id{tid}"
                               f"?i={e['trackId']}&theme=dark")
                        break
            except Exception:
                pass
        out["lecteur"] = {"type": "apple", "src": src}
    return out


def infos_youtube(c, f):
    pf = f.get("platforms") or {}
    cid = (pf.get("youtube") or {}).get("channelId")
    out = {}
    if cid:
        a = lire(f"https://www.youtube.com/channel/{cid}/about", cookie=YT_COOKIE)
        m = re.search(r'joinedDateText":\{"content":"[^"]*?(\d{4})"', a)
        if m:
            out["annee"] = int(m.group(1))
        v = lire(f"https://www.youtube.com/channel/{cid}/videos", cookie=YT_COOKIE)
        durees = [m for m in (minutes(x) for x in re.findall(
            r'"(?:simpleText|text|content)":"(\d{1,2}:\d{2}(?::\d{2})?)"', v)[:15]) if m]
        if durees:
            out["duree_min"] = round(statistics.median(durees))
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([\w-]{11})", (c.get("episode") or {}).get("url") or "")
    vid = m.group(1) if m else None
    if not vid and cid:
        # Jour d'episode MediaCritic : le lien enregistre est notre page, pas
        # une video de la chaine -> sa derniere video.
        m = re.search(r"<yt:videoId>([\w-]{11})</yt:videoId>",
                      lire(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
        vid = m.group(1) if m else None
    if vid:
        out["lecteur"] = {"type": "youtube", "src": f"https://www.youtube-nocookie.com/embed/{vid}"}
    return out


def infos_calculees(c, f):
    return infos_youtube(c, f) if c.get("type") == "youtube" else infos_podcast(c, f)


# --------------------------------------------------------------------------
# Notre avis : episode MediaCritic sur cette emission
# --------------------------------------------------------------------------
def notre_avis(slug):
    try:
        mc = json.loads((DATA / "mc_reviews.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    for num, r in mc.items():
        if r.get("slug") != slug or r.get("note") is None:
            continue
        page = r.get("page") or f"{slug}.html"
        sp = None
        try:
            man = json.loads((ROOT / "manifests" / f"ep{num}.json").read_text(encoding="utf-8"))
            sp = ((man.get("listen") or {}).get("spotify") or "")
        except Exception:
            pass
        if not sp:
            try:
                sp = (ROOT / "episodes" / page).read_text(encoding="utf-8")
            except Exception:
                sp = ""
        m = re.search(r"open\.spotify\.com/episode/(\w+)", sp)
        return {"note": r["note"], "episode": int(num), "url": f"episodes/{page}",
                "lecteur": f"https://open.spotify.com/embed/episode/{m.group(1)}" if m else None}
    return None


# --------------------------------------------------------------------------
# Indices et revelation
# --------------------------------------------------------------------------
LIB_CAT = {"societe": "société", "economie": "économie", "sante": "santé",
           "litterature": "littérature", "developpement personnel": "développement personnel",
           "jeu video": "jeu vidéo", "geopolitique": "géopolitique", "education": "éducation",
           "actualite": "actualité", "bien-etre": "bien-être", "cinema": "cinéma",
           "series": "séries", "decouverte": "découverte"}


def abonnes(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}".replace(".", ",").replace(",0", "") + " M"
    if n >= 1000:
        return f"{round(n / 1000)} k"
    return str(n)


def initiales(nom):
    mots = [m for m in re.split(r"[\s\-_.]+", nom or "") if m and m[0].isalpha()]
    return " ".join(m[0].upper() + "." for m in mots[:4])


def indices(c, f, info):
    yt = c.get("type") == "youtube"
    pf = f.get("platforms") or {}
    nb_abos = (pf.get("youtube") or {}).get("subscribers")
    nb_notes = (pf.get("apple") or {}).get("ratingCount")
    freq = f.get("frequence_jours")
    rythme = ("tous les jours" if freq is not None and freq <= 2 else
              "chaque semaine" if freq is not None and freq <= 9 else
              "tous les quinze jours" if freq is not None and freq <= 20 else
              f"tous les {freq} jours environ" if freq else None)
    # Reserve : remplace un indice dont la donnee manque (jamais d'invention).
    reserve = []
    if nb_abos:
        reserve.append(("Audience", f"{abonnes(nb_abos)} d'abonnés sur YouTube"))
    if nb_notes:
        reserve.append(("Audience", f"{nb_notes:,} notes sur Apple Podcasts".replace(",", " ")))
    if rythme:
        reserve.append(("Rythme", f"Publie {rythme}"))
    nb_ep = (pf.get("apple") or {}).get("episodeCount") or (pf.get("youtube") or {}).get("videoCount")
    if nb_ep:
        reserve.append(("Volume", f"Plus de {int(nb_ep) // 10 * 10 or nb_ep} {'vidéos' if yt else 'épisodes'}"))

    def ou_reserve(cle, texte):
        if texte:
            return {"cle": cle, "texte": texte}
        if reserve:
            k, t = reserve.pop(0)
            return {"cle": k, "texte": t}
        return {"cle": cle, "texte": "Pas de donnée sur ce point : essaie au flair !"}

    cats = c.get("categories") or f.get("categories") or []
    cat = LIB_CAT.get(cats[0], cats[0]) if cats else None
    genre = "Chaîne YouTube" if yt else "Podcast"
    i1 = {"cle": "Catégorie", "texte": f"{genre} · {cat}" if cat else genre}
    annee = info.get("annee")
    if annee and info.get("annee_min") and annee >= date.today().year - 1:
        annee = None        # « depuis au moins 2026 » n'apprend rien : indice de reserve
    i2 = ou_reserve("Année de création",
                    (f"Existe depuis au moins {annee}" if info.get("annee_min") else f"Lancé en {annee}")
                    if annee else None)
    dm = info.get("duree_min")
    fmt = None
    if dm:
        fmt = (f"{'Vidéos' if yt else 'Épisodes'} d'environ {dm} min"
               + (f", {'publiées' if yt else 'publiés'} {rythme}" if rythme else ""))
        reserve[:] = [r for r in reserve if r[0] != "Rythme"]
    i3 = ou_reserve("Format", fmt)
    if c.get("mode") == "episode":
        actu = "C'est l'émission du nouvel épisode de MediaCritic, sorti ce matin"
    elif c.get("sujet"):
        actu = f"Il a parlé ces jours-ci de « {c['sujet']} »"
    else:
        actu = None
    i4 = ou_reserve("L'actu du jour", actu)
    # Initiales : seulement si l'auteur n'est pas le nom de l'emission (sinon
    # l'indice donnerait la reponse : cas de la plupart des chaines YouTube).
    auteur = c.get("auteur") or f.get("author") or ""
    na, nt = normaliser(auteur), normaliser(c.get("titre"))
    if auteur and na and na not in nt and nt not in na:
        i5 = {"cle": "Initiales de l'auteur", "texte": initiales(auteur)}
    else:
        i5 = ou_reserve("Initiales de l'auteur", None)
    i6 = {"cle": "Pochette", "image": c.get("image") or f.get("image") or ""}
    return [i1, i2, i3, i4, i5, i6]


def alias(titre):
    """Reponses acceptees : le titre, et sa partie avant un sous-titre."""
    out = {normaliser(titre)}
    for sep in (" - ", " — ", " – ", " : ", " | ", " ("):
        if sep in titre:
            out.add(normaliser(titre.split(sep)[0]))
    out.discard("")
    return sorted(out)


def construire(c, info, corr):
    f = fiche(c["slug"])
    # Gabarit non rempli = rien a corriger : valeurs vides et cles « _ » ignorees.
    corr = {k: v for k, v in corr.items() if not k.startswith("_") and v not in ("", None, {}, [])}
    info = {**info, **{k: v for k, v in corr.items() if k in ("annee", "duree_min", "lecteur")}}
    if "annee" in corr:
        info.pop("annee_min", None)     # une annee corrigee a la main est exacte
    ind = indices(c, f, info)
    if corr.get("indices"):
        for i, v in corr["indices"].items():
            ind[int(i) - 1] = v
    avis = notre_avis(c["slug"])
    phrase = corr.get("phrase") or c.get("presentation") or ""
    phrase = re.sub(r"\s+", " ", phrase).strip()
    if len(phrase) > 220:
        phrase = phrase[:217].rsplit(" ", 1)[0] + "…"
    rev = {
        "titre": c["titre"],
        "auteur": corr.get("animateur") or c.get("auteur") or f.get("author") or "",
        "image": c.get("image") or f.get("image") or "",
        "phrase": phrase,
        "type": c.get("type") or "podcast",
        "episode": c.get("episode") or {},
        "lecteur": info.get("lecteur"),
        "fiche": f"fiches/{c['slug']}.html",
        "avis": avis,
    }
    if c.get("mode") != "episode":
        try:
            import ecoute
            el = ecoute.element_episode(f or {"slug": c["slug"]}, (c.get("episode") or {}).get("titre"),
                                        (c.get("episode") or {}).get("url"), c["titre"], rev["image"])
            if el:
                rev["ecoute"] = el
        except Exception:
            pass
    n = (date.fromisoformat(c["date"]) - LANCEMENT).days + 1
    charge = {"n": n, "r": [empreinte(a) for a in alias(c["titre"])],
              "indices": ind, "rev": rev}
    return base64.b64encode(json.dumps(charge, ensure_ascii=False).encode("utf-8")).decode("ascii")


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
TITRE = "Le Mystère du Jour — devine le podcast | MediaCritic"
DESC = ("Chaque jour, un podcast ou une chaîne YouTube à deviner en 6 indices. "
        "Joue, partage ton score et découvre l'émission du jour. Gratuit, sans inscription.")


def page():
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": f"{BASE}/mystere.html", "url": f"{BASE}/mystere.html",
         "name": TITRE, "description": DESC, "inLanguage": "fr-FR",
         "isPartOf": {"@id": BASE + "/#website"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Le Mystère du Jour",
             "item": f"{BASE}/mystere.html"}]}]}
    og = f"{BASE}/assets/mystere-og.png"
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
{MARQUEUR_LECTEURS}
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(TITRE)}</title>
<meta name="description" content="{h(DESC)}" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
<link rel="canonical" href="{BASE}/mystere.html" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE}/mystere.html" />
<meta property="og:title" content="Le Mystère du Jour : devine le podcast en 6 indices" />
<meta property="og:description" content="Un podcast à deviner chaque jour. Tu le trouves en combien ?" />
<meta property="og:image" content="{og}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="fr_FR" />
<meta property="og:site_name" content="MediaCritic" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@MediaCriticInc" />
<meta name="twitter:title" content="Le Mystère du Jour : devine le podcast en 6 indices" />
<meta name="twitter:description" content="Un podcast à deviner chaque jour. Tu le trouves en combien ?" />
<meta name="twitter:image" content="{og}" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet" />
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<link rel="stylesheet" href="/assets/mystere.css" />
</head>
<body>
<nav></nav>
<main class="mys" id="mys">
  <header class="mys-tete">
    <p class="mys-sur">🕵️ Le jeu quotidien de MediaCritic</p>
    <h1>Le Mystère du Jour</h1>
    <p class="mys-sous" id="mys-numero">Devine le podcast du jour en 6 indices.</p>
  </header>

  <section class="mys-jeu" id="mys-jeu" aria-labelledby="mys-titre-indices">
    <h2 id="mys-titre-indices" class="mys-vh">Les indices</h2>
    <ol class="mys-indices" id="mys-indices" aria-live="polite"></ol>
    <div class="mys-carres" id="mys-carres" aria-hidden="true"></div>
    <form class="mys-form" id="mys-form" autocomplete="off" novalidate>
      <label for="mys-saisie" class="mys-label">Ta proposition</label>
      <div class="mys-ligne">
        <input id="mys-saisie" class="mys-saisie" type="text" list="mys-noms" enterkeyhint="send"
               placeholder="Nom du podcast ou de la chaîne…" aria-describedby="mys-aide mys-retour" />
        <button type="submit" class="mys-btn mys-btn-plein">Valider</button>
      </div>
      <datalist id="mys-noms"></datalist>
      <p class="mys-aide" id="mys-aide">Accents et majuscules ne comptent pas.</p>
      <p class="mys-retour" id="mys-retour" role="status" aria-live="assertive"></p>
      <button type="button" class="mys-btn mys-btn-lien" id="mys-passer">Je donne ma langue au chat</button>
    </form>
    <ul class="mys-essais" id="mys-essais" aria-label="Tes propositions"></ul>
  </section>

  <section class="mys-attente" id="mys-attente" hidden>
    <h2>Le mystère du jour se prépare</h2>
    <p>Il arrive avec le podcast du jour, avant 10 h (heure de Paris). Reviens tout à l'heure !</p>
  </section>

  <section class="mys-revel" id="mys-revel" hidden aria-labelledby="mys-revel-titre"></section>

  <section class="mys-stats" id="mys-stats" aria-labelledby="mys-stats-titre">
    <h2 id="mys-stats-titre">Tes statistiques</h2>
    <dl class="mys-chiffres" id="mys-chiffres"></dl>
    <h3 class="mys-h3">Répartition des essais</h3>
    <ol class="mys-distrib" id="mys-distrib"></ol>
    <p class="mys-prochain">Prochain mystère dans <strong id="mys-compte">--:--:--</strong></p>
    <p class="mys-note" id="mys-stockage" hidden>Ton navigateur bloque l'enregistrement : la partie fonctionne, mais ta série ne sera pas conservée.</p>
  </section>

  <section class="mys-regles">
    <h2>Comment jouer</h2>
    <p>Chaque jour, un podcast ou une chaîne YouTube francophone se cache derrière six indices, du plus flou au plus évident : la catégorie, l'année de création, le format, l'actu du jour, les initiales de l'auteur, puis la pochette floutée. Chaque mauvaise réponse dévoile l'indice suivant.</p>
    <p>La réponse est <a href="podcast-du-jour.html">le podcast du jour</a> de MediaCritic, choisi chaque matin parce qu'il parle de l'actualité. Une partie par jour, nouveau mystère à minuit (heure de Paris). Tes séries et statistiques restent dans ton navigateur : aucune inscription, aucune donnée envoyée.</p>
  </section>
</main>
<footer></footer>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>
<script defer src="/assets/mystere.js"></script>
<script defer src="/assets/liste.js"></script>
<script defer src="/assets/partage.js"></script>
</body>
</html>"""
    html, etat = charte_appliquer(html, "accueil")
    assert etat is not None, "charte non appliquée"
    (ROOT / "mystere.html").write_text(html, encoding="utf-8")


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-reseau", action="store_true")
    a = ap.parse_args()
    hist = json.loads((DATA / "du_jour.json").read_text(encoding="utf-8"))["historique"]
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    try:
        corrections = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    except Exception:
        corrections = {}
    debut = (datetime.now(timezone.utc).date() - timedelta(days=FENETRE_JOURS)).isoformat()
    jours = {}
    for c in hist:
        if c.get("date", "") < debut or not c.get("slug") or not c.get("titre"):
            continue
        connu = cache.get(c["date"])
        if not connu or connu.get("slug") != c["slug"]:    # nouvelle date, ou choix refait
            if a.sans_reseau:
                # Rien en cache : on construit sans les donnees calculees, et on
                # N'ECRIT PAS le cache (sinon le vrai calcul ne serait jamais fait).
                jours[c["date"]] = construire(c, {}, corrections.get(c["date"]) or {})
                continue
            cache[c["date"]] = {"slug": c["slug"], **infos_calculees(c, fiche(c["slug"]))}
            print(f"  {c['date']} {c['titre']} : {sorted(k for k in cache[c['date']] if k != 'slug')}")
        jours[c["date"]] = construire(c, cache[c["date"]], corrections.get(c["date"]) or {})
    cache = {k: v for k, v in cache.items() if k >= debut}
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")

    # Saisie : palmares + tous les podcasts du jour passes (demande de
    # l'utilisateur). La reponse du jour y est forcement.
    noms = {}
    try:
        for r in json.loads((DATA / "mc_reviews.json").read_text(encoding="utf-8")).values():
            if r.get("title") and r.get("note") is not None:
                noms.setdefault(normaliser(r["title"]), r["title"])
    except Exception:
        pass
    for c in hist:
        if c.get("titre"):
            noms.setdefault(normaliser(c["titre"]), " ".join(c["titre"].split()))
    sortie = {"lancement": LANCEMENT.isoformat(), "jours": dict(sorted(jours.items())),
              "noms": sorted(noms.values(), key=lambda s: normaliser(s))}
    ancien = (DATA / "mystere.json").read_text(encoding="utf-8") if (DATA / "mystere.json").exists() else ""
    neuf = json.dumps(sortie, ensure_ascii=False, separators=(",", ":"))
    if neuf != ancien:
        (DATA / "mystere.json").write_text(neuf, encoding="utf-8")
    page()
    print(f"  mystere.json : {len(jours)} mystère(s), {len(noms)} noms pour la saisie")


if __name__ == "__main__":
    main()
