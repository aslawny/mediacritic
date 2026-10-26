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
        if est_info(c):
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


def recemment_mis_en_avant(hist, jour):
    lim = (jour - timedelta(days=SANS_REPETITION)).isoformat()
    return {h["slug"] for h in hist if h["date"] >= lim}


def plan_b(cat, hist, jour):
    """Pepite independante : bien notee, active, jamais mise en avant depuis
    180 jours. Choix deterministe pour la date (relance = meme resultat)."""
    lim = (jour - timedelta(days=180)).isoformat()
    deja = {h["slug"] for h in hist if h["date"] >= lim}
    actif = (jour - timedelta(days=90)).isoformat()
    cands = []
    for c in cat.values():
        if not c.get("independant") or c["slug"] in deja:
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
                for ep in eps:
                    if m in norm(ep["titre"]) and (not nom_seul or confirme(s, m, ep["titre"])):
                        trouves.append((score(s, c, ep, jour, rang_max[s["source"]]), s, c, ep))
    trouves.sort(key=lambda t: -t[0])
    for sc, s, c, ep in trouves[:8]:
        print(f"   {sc:5.2f}  [{s['sujet']}]  {c['title']} — « {ep['titre'][:70]} » ({ep['date']})")

    choix = {"date": jour.isoformat()}
    nb_info = sum(1 for c in cat.values() if est_info(c))
    ecarte_txt = (f"ce matin : {len(ecartes)} sujet(s) sensible(s) (drames, faits divers, "
                  f"guerres…), les {nb_info} émissions et chaînes d'information, et les "
                  f"émissions déjà mises en avant ces {SANS_REPETITION} derniers jours (et les "
                  f"sujets des 7 derniers jours).")
    if trouves:
        sc, s, c, ep = trouves[0]
        f = fiche(c["slug"]) or {}
        genre = "la vidéo" if c.get("type") == "youtube" else "l'épisode"
        publie = "publiée" if c.get("type") == "youtube" else "publié"
        source = ("parmi les articles les plus lus de Wikipédia en français hier"
                  if s["source"] == "wikipedia"
                  else "parmi les recherches en forte hausse sur Google en France")
        choix.update({
            "mode": "actu", "slug": c["slug"], "titre": c["title"], "type": c.get("type"),
            "auteur": c.get("author") or "", "image": c.get("image") or f.get("image") or "",
            "independant": bool(c.get("independant")), "mcNote": c.get("mcNote"),
            "sujet": s["sujet"], "source": s["source"],
            "episode": ep,
            "pourquoi": (f"« {s['sujet']} » figure {source}. {c['title']} y a consacré "
                         f"{genre} « {ep['titre']} », {publie} le {date_fr(ep['date'])}."),
            "presentation": phrase_description(c["slug"]),
        })
        # « Pourquoi ce choix » : comprehensible d'un coup d'oeil sur le site
        # (demande de l'utilisateur, 26/10/2026). Uniquement des faits.
        n = lambda x: f"{int(x):,}".replace(",", " ")
        if s["source"] == "wikipedia":
            force = (f"son article Wikipédia a été lu {n(s['poids'])} fois hier "
                     f"({s['rang']}{'er' if s['rang'] == 1 else 'e'} article le plus lu, hors pages techniques)")
        else:
            force = f"recherche en forte hausse sur Google en France ({n(s['poids'])}+ recherches)"
        age = (jour - date.fromisoformat(ep["date"])).days
        quand = "aujourd'hui" if age == 0 else "hier" if age == 1 else f"il y a {age} jours"
        audience = (f"{n(c['subscribers'])} abonnés YouTube" if c.get("type") == "youtube" and c.get("subscribers")
                    else f"{n(c['ratingCount'])} avis sur Apple Podcasts" if c.get("ratingCount") else "")
        atouts = [x for x in (
            audience,
            ("chaîne indépendante" if c.get("type") == "youtube" else "podcast indépendant")
            if c.get("independant") else "",
            (f"déjà critiquée par MediaCritic ({str(c['mcNote']).replace('.', ',')}/10)"
             if c.get("mcNote") else "")) if x]
        concurrents = len({t[2]["slug"] for t in trouves})
        choix["raisons"] = [
            ["🔥 Le sujet", f"« {s['sujet']} » : {force}."],
            ["🎧 La preuve", f"{genre[0].upper() + genre[1:]} « {ep['titre']} », {publie} "
                            f"le {date_fr(ep['date'])} ({quand})."],
            ["✅ Pourquoi elle", ((f"la seule émission de l'annuaire à avoir traité un sujet du jour "
                                   f"ces {FRAICHEUR_JOURS} derniers jours" if concurrents == 1 else
                                   f"meilleure correspondance parmi {concurrents} émissions ayant traité "
                                   f"un sujet du jour (sujet le plus consulté, épisode le plus récent, audience)")
                                  + (f" ; {', '.join(atouts)}" if atouts else "") + ".")],
            ["🚫 Écartés", ecarte_txt],
        ]
    else:
        c = plan_b(cat, hist, jour)
        if not c:
            print("Aucun choix possible (ni actu, ni pépite) : rien n'est écrit.")
            return
        note = f"{float(c['rating']):.1f}".replace(".", ",")
        nb = f"{int(c['ratingCount']):,}".replace(",", " ")
        choix.update({
            "mode": "pepite", "slug": c["slug"], "titre": c["title"], "type": c.get("type"),
            "auteur": c.get("author") or "", "image": c.get("image") or "",
            "independant": True, "mcNote": c.get("mcNote"),
            "pourquoi": (f"Aucune émission de notre annuaire n'a traité l'actualité du jour : "
                         f"place à une pépite indépendante, notée {note}/5 sur Apple Podcasts "
                         f"({nb} notes)."),
            "presentation": phrase_description(c["slug"]),
        })
        derniere = (fiche(c["slug"]) or {}).get("derniere_activite")
        choix["raisons"] = [
            ["🔎 Pas d'actu exploitable", (f"aucune des {len(entrees)} émissions suivies n'a publié "
                                          f"d'épisode sur les sujets du jour dans les {FRAICHEUR_JOURS} "
                                          f"derniers jours : nous ne forçons jamais le lien.")],
            ["💎 Pourquoi elle", (f"podcast indépendant noté {note}/5 sur Apple Podcasts ({nb} notes)"
                                 + (f", toujours actif (dernier épisode le {date_fr(derniere)})" if derniere else "")
                                 + ", jamais mis en avant ces 6 derniers mois.")],
            ["🚫 Écartés", ecarte_txt],
        ]
    choix["sujets_ecartes"] = len(ecartes)
    print(f"\n→ {choix['mode'].upper()} : {choix['titre']}\n  {choix['pourquoi']}")
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
