#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Le podcast du jour : choisit chaque matin l'emission de l'annuaire qui parle
de l'actualite du moment, et ecrit data/du_jour.json. Le rendu (accueil,
archive, kit reseaux, visuels) est fait par generate_du_jour.py.

Regle d'or (validee avec l'utilisateur, 25/10/2026) : on ne met une emission
en avant que si son lien avec l'actu est PROUVE par un episode reel, dont on
affiche le titre et la date. Aucun lien suppose, aucun texte invente. Quand
aucune emission ne colle, on le dit et on met en avant une pepite
independante (plan B), presentee comme telle.

Etapes :
  1. Sujets du jour : articles les plus lus de Wikipedia FR la veille + flux
     Google Trends France. Gratuits, sans cle.
  2. Sujets sensibles ecartes d'office (deces recents, attentats, faits
     divers avec victimes, guerres, contenus adultes) : on ne fait pas de
     trafic sur un drame.
  3. Vivier : ~600 emissions actives (analysees par MediaCritic, podcasts
     les plus suivis, chaines les plus suivies). Leurs episodes des 10
     derniers jours sont relus EN DIRECT (flux RSS / flux YouTube, sans
     quota) : la liste stockee dans les fiches n'est pas assez fraiche.
  4. Correspondance sujet <-> titre d'episode, score (force du sujet,
     fraicheur, audience, bonus independant / analyse), pas de repetition
     sur 30 jours.

Usage :
  python scripts/du_jour.py              # choisit et ecrit data/du_jour.json
  python scripts/du_jour.py --dry-run    # affiche le choix sans rien ecrire
  python scripts/du_jour.py --date 2026-10-25
"""
import argparse
import hashlib
import html
import json
import math
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from enrich_episodes import _lire, _texte  # noqa: E402
from independance import _mots, est_independant  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
SORTIE = DATA / "du_jour.json"
MC_REVIEWS = (json.loads((DATA / "mc_reviews.json").read_text(encoding="utf-8"))
              if (DATA / "mc_reviews.json").exists() else {})
UA = {"User-Agent": "MediaCriticBot/1.0 (https://www.mediacritic.fr; mediacriticinc@gmail.com)"}

FRAICHEUR_JOURS = 10       # un episode plus ancien ne « parle » plus de l'actu
SANS_REPETITION = 30       # jours avant de remettre la meme emission en avant
VIVIER_PODCASTS = 400
VIVIER_CHAINES = 200
HISTORIQUE_MAX = 400

# --------------------------------------------------------------------------
# Sujets sensibles : exclusion stricte (choix de l'utilisateur, 25/10/2026).
# Compare sans accents, en minuscules, sur le titre ET la description
# Wikipedia (ou les titres d'articles lies pour Google Trends).
# --------------------------------------------------------------------------
SENSIBLES = re.compile(
    r"\b(fusillade|attentat|attaque|terroris\w*|meurtre|meurtrier|assassin\w*|"
    r"tuerie|massacre|homicide|feminicide|infanticide|viol|violee?s?|"
    r"pedocrimin\w*|pedophil\w*|inceste|enlevement|sequestration|otage|"
    r"disparition|disparue?|mort|morte|morts|deces|decede\w*|obseques|funerailles|"
    r"hommage|suicide|accident|crash|catastrophe|seisme|tremblement|inondation|"
    r"incendie|naufrage|explosion|guerre|bombardement|conflit|genocide|"
    r"criminel|criminelle|tueur|tueuse|nazi\w*|affaire|proces|condamne\w*|"
    r"agression|victime\w*|blesse\w*|porno\w*|xxx|sexe|sexuel\w*)\b")
# Un deces de l'annee en cours dans la description Wikipedia : « (1950-2026) ».
DECES_RECENT = re.compile(r"\b\d{3,4}\s*[-–]\s*%d\b" % date.today().year)

# Articles Wikipedia sans valeur d'actualite.
WIKI_IGNORES = re.compile(
    r"^(Wikipédia:|Spécial:|Special:|Portail:|Aide:|Fichier:|Modèle:|Catégorie:)"
    r"|^(Cookie|XXX|Google|YouTube|Facebook|Instagram|Wikipédia|ChatGPT|Netflix)\b"
    r"|^Liste_de|^Liste_des|^Décès_en|^Élection_présidentielle")

# Mots trop vagues pour etre un sujet a eux seuls (Google Trends en remonte).
VAGUES = set("""pere mere contrat meteo heure match resultat resultats direct
programme tele film serie video photo france paris jeudi vendredi samedi
dimanche lundi mardi mercredi aujourdhui demain hier score classement
monde vie jour temps gens histoire monde coeur amour argent travail""".split())
MOTS_VIDES = set("""le la les l un une des de du d et ou en a au aux pour par sur avec
dans ce cette ces son sa ses leur leurs qui que quoi est sont the of and""".split())


def significatifs(texte):
    return [m for m in norm(texte).split() if m not in MOTS_VIDES and m not in VAGUES and len(m) >= 4]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", s).strip() + " "


try:  # magasin de certificats a jour si disponible (Windows en local)
    import certifi
    import ssl
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL = None


def lire_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return json.loads(r.read().decode("utf-8"))


def lire_texte(url, timeout=20):
    req = urllib.request.Request(url, headers={**UA, "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return r.read().decode("utf-8", "replace")


# --------------------------------------------------------------------------
# 1. Sujets du jour
# --------------------------------------------------------------------------
def sujets_wikipedia(jour):
    veille = jour - timedelta(days=1)
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/top/fr.wikipedia/"
           f"all-access/{veille:%Y/%m/%d}")
    try:
        arts = lire_json(url)["items"][0]["articles"]
    except Exception as e:
        print(f"  ! Wikipédia indisponible : {e}")
        return []
    sujets = []
    for a in arts:
        t = a["article"]
        if WIKI_IGNORES.search(t):
            continue
        sujets.append({"titre_wiki": t, "vues": a["views"]})
        if len(sujets) >= 40:
            break
    # Description courte de chaque article : sert au filtre des sujets
    # sensibles (« criminel de guerre nazi », « (1950-2026) »…).
    def resume(s):
        try:
            r = lire_json("https://fr.wikipedia.org/api/rest_v1/page/summary/"
                          + urllib.parse.quote(s["titre_wiki"], safe=""))
            s["description"] = (r.get("description") or "")
            s["extrait"] = (r.get("extract") or "")[:400]
        except Exception:
            s["description"], s["extrait"] = "", ""
        return s
    with ThreadPoolExecutor(8) as ex:
        sujets = list(ex.map(resume, sujets))
    out = []
    for rang, s in enumerate(sujets, 1):
        lib = re.sub(r"\s*\(.*?\)\s*$", "", s["titre_wiki"].replace("_", " ")).strip()
        out.append({"sujet": lib, "source": "wikipedia", "rang": rang, "poids": s["vues"],
                    "contexte": f'{s["description"]} {s["extrait"]}',
                    "personne": bool(re.search(r"\bnée? (le|en)\b", s["extrait"]))})
    return out


def sujets_trends():
    try:
        x = lire_texte("https://trends.google.com/trending/rss?geo=FR")
    except Exception as e:
        print(f"  ! Google Trends indisponible : {e}")
        return []
    out = []
    for rang, it in enumerate(re.findall(r"<item>(.*?)</item>", x, re.S), 1):
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        tr = re.search(r"<ht:approx_traffic>([\d,.]+)", it)
        if not t:
            continue
        lib = _texte(t.group(1))
        if lib == lib.lower():   # Google Trends ecrit « le havre » : affichage « Le Havre »
            lib = " ".join(w if w in ("de", "du", "des", "la", "le", "les", "et", "vs", "d", "l")
                           and i else w[:1].upper() + w[1:] for i, w in enumerate(lib.split()))
        trafic = int(re.sub(r"\D", "", tr.group(1))) if tr else 0
        liees = " ".join(_texte(n) for n in re.findall(r"<ht:news_item_title>(.*?)</ht:news_item_title>", it, re.S))
        mots = significatifs(lib)
        # « père », « contrat », « le monde » : pas des sujets d'actualite.
        if not mots or (len(mots) == 1 and (len(mots[0]) < 5 or trafic < 2000)):
            continue
        out.append({"sujet": lib, "source": "trends", "rang": rang, "poids": trafic,
                    "contexte": liees, "personne": False})
    return out


def titres_presse(sujet, maxi=1):
    """Titre de presse des 3 derniers jours sur le sujet (Google Actualites),
    avec sa source : c'est ce qui RESUME l'actu, sans rien inventer. Reseaux
    sociaux et titres sensibles ecartes. Parmi les 8 plus recents, on garde le
    plus COURT qui nomme le sujet (le plus parlant : « Harry Kane entre dans la
    legende » plutot qu'un sondage de 30 mots)."""
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(f'"{sujet}" when:3d')
           + "&hl=fr&gl=FR&ceid=FR:fr")
    try:
        x = lire_texte(url)
    except Exception:
        return []
    out = []
    for it in re.findall(r"<item>(.*?)</item>", x, re.S):
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        if not t:
            continue
        titre, _, src = _texte(t.group(1)).rpartition(" - ")
        if not titre or not src:
            continue
        if re.search(r"facebook|youtube|instagram|tiktok|twitter|linkedin|^x$", src.strip(), re.I):
            continue
        if SENSIBLES.search(norm(titre).strip()):
            continue
        if norm(sujet).strip() not in norm(titre):
            continue
        out.append((titre, src.strip()))
        if len(out) >= 8:
            break
    out.sort(key=lambda t: len(t[0].split()))
    choisis = []
    for titre, src in out[:maxi]:
        mots = titre.split()
        if len(mots) > 14:
            titre = " ".join(mots[:14]).rstrip(",;:") + "…"
        choisis.append((titre, src))
    return choisis


def est_sensible(s):
    texte = norm(s["sujet"] + " " + s.get("contexte", ""))
    if SENSIBLES.search(texte.strip()):
        return True
    return bool(DECES_RECENT.search(s.get("contexte", "")))


# --------------------------------------------------------------------------
# 2. Vivier d'emissions actives et leurs episodes frais
# --------------------------------------------------------------------------
def charger_catalogue():
    cat = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    return {c["slug"]: c for c in cat}


def fiche(slug):
    p = DATA / "content" / f"{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# --------------------------------------------------------------------------
# Emissions et chaines d'information : exclues (choix de l'utilisateur,
# 26/10/2026). Le premier passage automatique avait choisi LCI. Mettre en
# avant une chaine d'info sur l'actu du jour n'apprend rien au visiteur :
# le podcast du jour doit faire decouvrir une emission qui RACONTE ou
# ANALYSE le sujet. Une emission est « d'info » si sa categorie PRINCIPALE
# est l'actualite (la categorie seule est trop large : Les Grosses Tetes y
# figurent), ou si elle appartient a un media d'information.
# --------------------------------------------------------------------------
CATEGORIES_INFO = {"actualite", "news"}
MEDIAS_INFO = [_mots(m) for m in (
    "lci", "bfmtv", "bfm", "franceinfo", "france info", "france 24", "cnews", "rfi",
    "le monde", "mediapart", "brut", "le media", "blast", "tf1 info", "euronews",
    "africanews", "tv5monde", "radio canada info", "konbini news", "loopsider",
    "hugodecrypte", "hugo decrypte", "20 minutes", "le parisien", "le figaro",
    "liberation", "l express", "le point", "ouest france", "huffpost", "reuters", "afp")]


# Marques de paris sportifs : jamais mises en avant (28/10/2026 : le moteur
# avait retenu « WINAMAX FOOTBALL CLUB », emission d'un bookmaker).
MARQUES_EXCLUES = [_mots(m) for m in ("winamax", "betclic", "unibet", "parions sport",
                                      "pmu", "fdj", "bwin", "zebet", "pokerstars")]


def est_marque_exclue(c):
    noms = _mots(c.get("title")) + _mots(c.get("author"))
    return any(m in noms for m in MARQUES_EXCLUES)


def est_info(c):
    cats = c.get("categories") or []
    if cats and cats[0] in CATEGORIES_INFO:
        return True
    noms = _mots(c.get("title")) + _mots(c.get("author"))
    return any(m in noms for m in MEDIAS_INFO)


def vivier(cat, jour):
    feeds = json.loads((DATA / "_feed_urls.json").read_text(encoding="utf-8")) \
        if (DATA / "_feed_urls.json").exists() else {}
    limite_active = (jour - timedelta(days=60)).isoformat()
    pods, chaines = [], []
    for c in cat.values():
        if est_info(c) or est_marque_exclue(c):
            continue
        # Chaines YouTube : seulement les independantes. Les autres sont des
        # clubs, marques, medias ou artistes en label (le moteur avait choisi
        # la chaine de l'OM pour une video en anglais) : pas des emissions a
        # faire decouvrir.
        if c.get("type") == "youtube" and not c.get("independant"):
            continue
        if c.get("type") == "youtube":
            if c.get("subscribers"):
                chaines.append(c)
        elif feeds.get(c["slug"]) and (c.get("ratingCount") or c.get("hasMediacritic")):
            pods.append(c)
    pods.sort(key=lambda c: (not c.get("hasMediacritic"), -(c.get("ratingCount") or 0)))
    chaines.sort(key=lambda c: (not c.get("hasMediacritic"), -(c.get("subscribers") or 0)))
    choix = []
    for c in pods[:VIVIER_PODCASTS * 2]:
        f = fiche(c["slug"]) or {}
        if c.get("hasMediacritic") or (f.get("derniere_activite") or "") >= limite_active:
            choix.append(("podcast", c, feeds[c["slug"]]))
        if sum(1 for t in choix if t[0] == "podcast") >= VIVIER_PODCASTS:
            break
    for c in chaines[:VIVIER_CHAINES]:
        cid = ((fiche(c["slug"]) or {}).get("platforms", {}).get("youtube", {}) or {}).get("channelId")
        if cid:
            choix.append(("youtube", c, cid))
    return choix


def episodes_frais(entree, jour):
    """Episodes des FRAICHEUR_JOURS derniers jours : [{titre, date, url}]."""
    genre, c, src = entree
    limite = jour - timedelta(days=FRAICHEUR_JOURS)
    eps = []
    try:
        if genre == "podcast":
            x = _lire(src)
            for it in re.findall(r"<item[ >](.*?)</item>", x, re.S)[:15]:
                t = re.search(r"<title>(.*?)</title>", it, re.S)
                d = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
                lien = re.search(r"<link>(.*?)</link>", it, re.S)
                if not (t and d):
                    continue
                try:
                    dt = parsedate_to_datetime(d.group(1).strip()).date()
                except Exception:
                    continue
                if limite <= dt <= jour:
                    u = _texte(lien.group(1)) if lien else ""
                    eps.append({"titre": _texte(t.group(1))[:160], "date": dt.isoformat(),
                                "url": u if u.startswith("http") else ""})
        else:
            x = _lire("https://www.youtube.com/feeds/videos.xml?channel_id=" + src, ko=80)
            for e in re.findall(r"<entry>(.*?)</entry>", x, re.S)[:15]:
                t = re.search(r"<media:title>(.*?)</media:title>", e, re.S)
                d = re.search(r"<published>(.*?)</published>", e)
                v = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
                if not (t and d and v):
                    continue
                dt = datetime.fromisoformat(d.group(1).strip().replace("Z", "+00:00")).date()
                if limite <= dt <= jour:
                    eps.append({"titre": _texte(t.group(1))[:160], "date": dt.isoformat(),
                                "url": "https://www.youtube.com/watch?v=" + v.group(1)})
    except Exception:
        return c, []
    return c, eps


# --------------------------------------------------------------------------
# 3. Correspondance et score
# --------------------------------------------------------------------------
def motifs(s):
    """Formes acceptees du sujet dans un titre d'episode : (motif, mot_seul)."""
    mots = norm(s["sujet"]).split()
    m = [(norm(s["sujet"]), len(mots) == 1)]
    # Une personne est souvent citee par son seul nom (« Messi »).
    if s.get("personne") and len(mots) >= 2 and len(mots[-1]) >= 5 and mots[-1] not in VAGUES:
        m.append((" " + mots[-1] + " ", True))
    return m


def sans_accent(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def nom_propre(mot, titre):
    """Le nom seul doit figurer avec une majuscule (« Messi », pas « messie »)."""
    return re.search(r"" + mot.strip().capitalize() + r"", sans_accent(titre)) is not None


def confirme(s, mot, titre):
    """Un mot seul est ambigu : « Zazie » (la chanteuse, sujet Wikipedia)
    accrochait un episode sur « Zazie dans le metro ». On exige qu'un autre
    mot significatif du contexte du sujet figure aussi dans le titre."""
    if not nom_propre(mot, titre):
        return False
    contexte = set(significatifs(s.get("contexte", ""))) - {mot.strip()}
    return bool(contexte & set(significatifs(titre)))


def score(s, c, ep, jour, rang_max):
    force = 1 - (s["rang"] - 1) / max(rang_max, 1)            # 0..1
    age = (jour - date.fromisoformat(ep["date"])).days
    fraicheur = 1.0 if age <= 3 else 0.7 if age <= 7 else 0.4
    aud = c.get("ratingCount") or (c.get("subscribers") or 0) / 1000
    audience = min(math.log10(1 + aud) / 4, 1)                  # 0..1
    bonus = (0.3 if c.get("independant") else 0) + (0.2 if c.get("hasMediacritic") else 0)
    return round(2 * force + fraicheur + audience + bonus, 4)


# --------------------------------------------------------------------------
# Thematique : jamais deux fois de suite la meme (choix de l'utilisateur,
# 28/10/2026 : trois choix football en quatre jours). La thematique est la
# categorie PRINCIPALE de la fiche, regroupee en familles pour que la regle
# ait un sens (football, running et sport = une seule famille).
# --------------------------------------------------------------------------
FAMILLES = {
    "sport": {"sport", "football", "running", "endurance", "basket", "rugby", "tennis",
              "cyclisme", "fitness", "musculation", "golf", "f1", "sports"},
    "cinema": {"cinema", "series", "television"},
    "business": {"business", "entrepreneuriat", "investissement", "marketing", "management",
                 "economie", "carriere", "finance"},
    "bien-etre": {"developpement personnel", "psychologie", "bien-etre", "sante",
                  "spiritualite", "meditation"},
    "jeu video": {"gaming", "jeux", "jeux video", "jeux inde", "retro"},
    "histoire": {"histoire", "true crime", "documentaire"},
}
_FAMILLE_DE = {cat: fam for fam, cats in FAMILLES.items() for cat in cats}


def thematique(c):
    cats = c.get("categories") or []
    if not cats:
        return None
    return _FAMILLE_DE.get(cats[0], cats[0])


# Thematique du SUJET, lue dans sa description Wikipedia / les titres lies :
# une chaine classee « anime » qui parle du Ballon d'Or traite bien du sport.
MOTS_THEME = {
    "sport": r"footballeu|football|ballon d or|ligue 1|ligue des champions|mercato|"
             r"joueur de (tennis|rugby|basket)|rugbyman|cycliste|athlete|pilote de|"
             r"club de|selection nationale|coupe du monde|jeux olympiques|nba|match",
    "cinema": r"acteur|actrice|realisateur|realisatrice|film|serie televisee",
    "musique": r"chanteur|chanteuse|rappeur|rappeuse|album|groupe de musique|musicien",
    "jeu video": r"jeu video|jeux video|console",
}


def thematique_sujet(s):
    t = norm(s.get("sujet", "") + " " + s.get("contexte", ""))
    for fam, motif in MOTS_THEME.items():
        if re.search(r" (" + motif + r")", t):
            return fam
    return None


def thematique_veille(hist, jour, cat):
    """Thematique du dernier choix avant `jour` (calculee si absente)."""
    for h in hist:
        if h["date"] < jour.isoformat():
            return h.get("thematique") or thematique(cat.get(h["slug"], {}))
    return None


def recemment_mis_en_avant(hist, jour):
    lim = (jour - timedelta(days=SANS_REPETITION)).isoformat()
    return {h["slug"] for h in hist if h["date"] >= lim}


def plan_b(cat, hist, jour, theme_interdit=None):
    """Pepite independante : bien notee, active, jamais mise en avant depuis
    180 jours. Choix deterministe pour la date (relance = meme resultat)."""
    lim = (jour - timedelta(days=180)).isoformat()
    deja = {h["slug"] for h in hist if h["date"] >= lim}
    actif = (jour - timedelta(days=90)).isoformat()
    cands = []
    for c in cat.values():
        if not c.get("independant") or c["slug"] in deja:
            continue
        if theme_interdit and thematique(c) == theme_interdit:
            continue
        if float(c.get("rating") or 0) < 4.7 or int(c.get("ratingCount") or 0) < 100:
            continue
        if ((fiche(c["slug"]) or {}).get("derniere_activite") or "") < actif:
            continue
        cands.append(c)
    cands.sort(key=lambda c: -int(c["ratingCount"]))
    cands = cands[:60]
    if not cands:
        return None
    i = int(hashlib.sha1(jour.isoformat().encode()).hexdigest(), 16) % len(cands)
    return cands[i]


def phrase_description(slug, maxi=230):
    d = ((fiche(slug) or {}).get("description") or "").strip()
    d = re.sub(r"https?://\S+", "", d)
    # On garde le texte de presentation, pas les mentions pratiques des
    # descriptions YouTube (reseaux sociaux, adresse de contact, partenariats).
    d = re.split(r"\n\s*\n|mes r[ée]seaux|r[ée]seaux sociaux|instagram|partenariat|"
                 r"contact|business|@[\w.]+|[\w.+-]+@[\w-]+\.", d, maxsplit=1, flags=re.I)[0]
    d = re.sub(r"\s+", " ", d).strip(" -–:•|")
    phrases = [p.strip(" ➡→•-–:") for p in re.split(r"(?<=[.!?])\s+|➡|→|•", d)]
    # Appels a l'action (« Abonnez-vous », « Souscrivez », newsletter) : pas
    # une presentation de l'emission.
    phrases = [p for p in phrases if p and not re.search(
        r"abonne|souscri|newsletter|premium|soutenez|tipeee|patreon|lien|cliquez", p, re.I)]
    out = ""
    for p in phrases:
        if len(out) + len(p) > maxi:
            break
        out = (out + " " + p).strip()
    return out or (d[:maxi].rsplit(" ", 1)[0] + "…" if d else "")


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]


def date_fr(iso):
    d = date.fromisoformat(iso)
    return f"{d.day if d.day > 1 else '1er'} {MOIS[d.month - 1]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date")
    a = ap.parse_args()
    jour = date.fromisoformat(a.date) if a.date else datetime.now(timezone.utc).date()

    etat = json.loads(SORTIE.read_text(encoding="utf-8")) if SORTIE.exists() else {"historique": []}
    hist = etat["historique"]
    if any(h["date"] == jour.isoformat() for h in hist) and not a.dry_run:
        print(f"Podcast du jour déjà choisi pour le {jour} : rien à faire.")
        return

    print("1. Sujets du jour")
    sujets = sujets_wikipedia(jour) + sujets_trends()
    gardes, ecartes = [], []
    for s in sujets:
        (ecartes if est_sensible(s) else gardes).append(s)
    print(f"   {len(sujets)} sujets, {len(ecartes)} écartés (sensibles), {len(gardes)} retenus")
    for s in ecartes[:12]:
        print(f"     ✗ {s['sujet']}")

    print("2. Épisodes frais du vivier")
    cat = charger_catalogue()
    entrees = vivier(cat, jour)
    with ThreadPoolExecutor(24) as ex:
        frais = [r for r in ex.map(lambda e: episodes_frais(e, jour), entrees) if r[1]]
    print(f"   {len(entrees)} émissions relues, {len(frais)} avec un épisode de moins de {FRAICHEUR_JOURS} jours")

    print("3. Correspondances")
    bloques = recemment_mis_en_avant(hist, jour)
    theme_veille = thematique_veille(hist, jour, cat)
    if theme_veille:
        print(f"   thématique de la veille écartée : {theme_veille}")
    rang_max = {"wikipedia": 40, "trends": 30}
    tous_titres = [norm(ep["titre"]) for _, eps in frais for ep in eps]
    # Un « sujet » present dans plus de 1 % des titres du jour est une
    # expression banale (« le monde » remontait de Google Trends), pas une
    # actualite : il accrocherait n'importe quel episode.
    seuil_banal = max(5, len(tous_titres) // 100)
    # Un meme sujet ne revient pas avant 7 jours (Laurent Nunez, choisi la
    # veille, ressortait le lendemain via une autre emission).
    lim_sujet = (jour - timedelta(days=7)).isoformat()
    sujets_recents = {norm(h.get("sujet") or "") for h in hist if h["date"] >= lim_sujet}
    trouves = []
    exclus_theme = set()   # emissions qui collaient a l'actu, mais du theme de la veille
    for s in gardes:
        if norm(s["sujet"]) in sujets_recents:
            continue
        for m, nom_seul in motifs(s):
            if sum(1 for t in tous_titres if m in t) > seuil_banal:
                print(f"     ~ « {s['sujet']} » trop banal ({m.strip()}), ignoré")
                continue
            for c, eps in frais:
                if c["slug"] in bloques:
                    continue
                if theme_veille and theme_veille in (thematique(c), thematique_sujet(s)):
                    if any(m in norm(ep["titre"]) for ep in eps):
                        exclus_theme.add(c["slug"])
                    continue
                for ep in eps:
                    if m in norm(ep["titre"]) and (not nom_seul or confirme(s, m, ep["titre"])):
                        trouves.append((score(s, c, ep, jour, rang_max[s["source"]]), s, c, ep))
    trouves.sort(key=lambda t: -t[0])
    for sc, s, c, ep in trouves[:8]:
        print(f"   {sc:5.2f}  [{s['sujet']}]  {c['title']} — « {ep['titre'][:70]} » ({ep['date']})")

    choix = {"date": jour.isoformat()}
    # ------------------------------------------------------------------
    # Texte affiche : TROIS sections, rien d'autre (demande de l'utilisateur,
    # 28/10/2026) — « L'actu qui a fait le buzz », « L'émission »,
    # « Pourquoi l'écouter ». Les REGLES de selection (sujets ecartes,
    # emissions d'info, alternance, repetition…) ne s'affichent JAMAIS :
    # elles restent internes. Uniquement des faits : chiffres reels, titres de
    # presse cites avec leur source, titre et date de l'episode.
    # ------------------------------------------------------------------
    n = lambda x: f"{int(x):,}".replace(",", " ")

    def buzz(s):
        if s["source"] == "wikipedia":
            force = f"« {s['sujet']} » a été l'un des sujets les plus lus de Wikipédia hier ({n(s['poids'])} lectures)."
        else:
            force = f"« {s['sujet']} » s'envole dans les recherches Google en France ({n(s['poids'])}+ recherches)."
        titres = titres_presse(s["sujet"])
        if titres:
            return force + " À la une : " + " ; ".join(f"« {t} » ({src})" for t, src in titres) + "."
        d = re.split(r"(?<=[.!?])\s+", (s.get("contexte") or "").strip())
        return force + (f" {d[0]}" if d and len(d[0]) < 220 else "")

    def emission(c):
        typ = "Chaîne YouTube" if c.get("type") == "youtube" else "Podcast"
        auteur = (c.get("author") or "").strip()
        tete = f"{c['title']} — {typ.lower()}" + (f" de {auteur}" if auteur and norm(auteur) != norm(c["title"]) else "")
        pres = html.unescape(phrase_description(c["slug"], maxi=200))
        # Les fiches deja critiquees portent NOTRE texte de referencement
        # (« Critique et analyse du podcast… ») : on montre notre verdict.
        if not pres or pres.startswith("Critique et analyse"):
            verdict = next((v.get("verdict") for v in MC_REVIEWS.values()
                            if v.get("slug") == c["slug"] and v.get("verdict")), None)
            pres = f"Notre verdict : « {verdict} »" if verdict else ""
        return f"{tete}. {pres}" if pres else f"{tete}."

    def qualites(c):
        """« Une émission indépendante, notée 4,6/5 sur Apple Podcasts (187
        notes). » — toujours au féminin d'« émission », quel que soit le nom."""
        parts = []
        if c.get("type") == "youtube" and c.get("subscribers"):
            parts.append(f"suivie par {n(c['subscribers'])} abonnés sur YouTube")
        elif c.get("rating") and c.get("ratingCount"):
            parts.append(f"notée {float(c['rating']):.1f}".replace(".", ",")
                         + f"/5 sur Apple Podcasts ({n(c['ratingCount'])} notes)")
        if c.get("mcNote"):
            parts.append(f"{str(c['mcNote']).replace('.', ',')}/10 dans notre critique")
        tete = "Une émission" + (" indépendante" if c.get("independant") else "")
        if not parts:
            return (tete + ".") if c.get("independant") else ""
        return f"{tete} {parts[0]}" + "".join(f", {p}" for p in parts[1:]) + "."

    def court(titre, maxi=12):
        mots = titre.split()
        return titre if len(mots) <= maxi else " ".join(mots[:maxi]).rstrip(",;:–-") + "…"

    sujet_buzz = trouves[0][1] if trouves else (gardes[0] if gardes else None)
    if trouves:
        sc, s, c, ep = trouves[0]
        f = fiche(c["slug"]) or {}
        genre = "sa vidéo" if c.get("type") == "youtube" else "son épisode"
        publie = "publiée" if c.get("type") == "youtube" else "publié"
        choix.update({
            "mode": "actu", "slug": c["slug"], "titre": c["title"], "type": c.get("type"),
            "auteur": c.get("author") or "", "image": c.get("image") or f.get("image") or "",
            "independant": bool(c.get("independant")), "mcNote": c.get("mcNote"),
            "sujet": s["sujet"], "source": s["source"],
            "episode": ep,
            "pourquoi": (f"« {s['sujet']} » fait l'actu : {c['title']} y a consacré "
                         f"{genre} « {ep['titre']} », {publie} le {date_fr(ep['date'])}."),
            "presentation": phrase_description(c["slug"]),
        })

        choix["sections"] = [
            ["L'actu qui a fait le buzz", buzz(s)],
            ["L'émission", emission(c)],
            ["Pourquoi l'écouter", (f"Pour prolonger l'actu : dans {genre} « {court(ep['titre'])} », {publie} le "
                                    f"{date_fr(ep['date'])}, {c['title']} revient justement sur « {s['sujet']} ». "
                                    + qualites(c)).strip()],
        ]
    else:
        c = plan_b(cat, hist, jour, theme_veille)
        if not c:
            print("Aucun choix possible (ni actu, ni pépite) : rien n'est écrit.")
            return
        note = f"{float(c['rating']):.1f}".replace(".", ",")
        nb = n(c["ratingCount"])
        choix.update({
            "mode": "pepite", "slug": c["slug"], "titre": c["title"], "type": c.get("type"),
            "auteur": c.get("author") or "", "image": c.get("image") or "",
            "independant": True, "mcNote": c.get("mcNote"),
            "pourquoi": f"La pépite du jour : {c['title']}, podcast indépendant noté {note}/5 sur Apple Podcasts ({nb} notes).",
            "presentation": phrase_description(c["slug"]),
        })
        sections = []
        if sujet_buzz:
            sections.append(["L'actu qui a fait le buzz", buzz(sujet_buzz)])
        sections += [
            ["L'émission", emission(c)],
            ["Pourquoi l'écouter", (f"Pour souffler entre deux actus avec une pépite indépendante, "
                                    f"notée {note}/5 sur Apple Podcasts par {nb} auditeurs.")],
        ]
        choix["sections"] = sections

    choix["thematique"] = ((thematique_sujet(trouves[0][1]) if trouves else None)
                           or thematique(cat.get(choix["slug"], {})))
    print(f"\n→ {choix['mode'].upper()} : {choix['titre']}\n  {choix['pourquoi']}")
    for t, v in choix.get("sections", []):
        print(f"  ## {t} : {v}")
    if a.dry_run:
        return
    hist.insert(0, choix)
    etat["historique"] = hist[:HISTORIQUE_MAX]
    SORTIE.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    # La fiche de l'emission affiche la mention « Podcast du jour » : on la
    # marque comme modifiee pour que generate_fiches.py la regenere.
    p = DATA / "content" / f"{choix['slug']}.json"
    if p.exists():
        os.utime(p)
    print(f"data/du_jour.json écrit ({len(etat['historique'])} jour(s) d'historique)")


if __name__ == "__main__":
    main()
