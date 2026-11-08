#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ajoute aux fiches les derniers episodes, la frequence de publication et la
date de derniere activite -- trois informations qu'attend tout annuaire et qui
manquaient totalement : le modele ne contenait que `episodeCount`.

Sources, toutes publiques et sans quota d'API :
  - podcasts : flux RSS (feedUrl resolu via lookup iTunes, mis en cache) ;
  - chaines YouTube : flux videos.xml de la chaine.

Champs ecrits dans data/content/{slug}.json :
    episodes_recents   [{titre, date}]  -- 5 au plus
    derniere_activite  AAAA-MM-JJ
    frequence_jours    ecart median entre publications

Budget par execution (--limit) : la charge s'etale sur plusieurs nuits plutot
que de lancer 8 000 requetes d'un coup. Les echecs sont memorises et ne sont
pas retentes avant 30 jours.

Rotation permanente (08/11/2026) : les fiches deja remplies sont relues, les
plus suivies et les emissions critiquees chaque semaine, les autres selon leur
activite (14, 45 ou 90 jours). Une fiche n'est reecrite que si elle a change.

Tous les podcasts ne sont pas couverts : certains n'exposent aucun feedUrl via
iTunes (verifie sur « Face a l'histoire »). C'est attendu, pas une erreur.

Usage :
  python scripts/enrich_episodes.py --dry-run
  python scripts/enrich_episodes.py --limit 300
"""
import argparse
import glob
import html as _html
import json
import re
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "content"
ETAT = ROOT / "data" / "_eps_state.json"
FEEDS = ROOT / "data" / "_feed_urls.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; MediaCriticBot/1.0)"}
MAX_EPISODES = 5
RETENTER_APRES = 30
# Rotation : jours entre deux relectures d'une fiche deja remplie.
TAILLE_TETE = 500         # les plus suivies (avis Apple ou abonnes)
INTERVALLE_TETE = 7       # tete + emissions critiquees
INTERVALLE_ACTIF = 14     # un episode depuis moins de 60 jours
INTERVALLE_AUTRE = 45
INTERVALLE_DORMANT = 90   # rien depuis plus d'un an


def _texte(x):
    x = re.sub(r"<!\[CDATA\[|\]\]>", "", x or "")
    x = re.sub(r"<[^>]+>", "", x)
    for _ in range(2):
        x = _html.unescape(x)
    return re.sub(r"\s+", " ", x).strip()


def _lire(url, ko=140, timeout=25):
    req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-%d" % (ko * 1024)})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        brut = r.read(ko * 1024 + 1)
    # YouTube repond en gzip a une requete Range, meme sans Accept-Encoding :
    # sans cette ligne, le flux est illisible et paraissait vide (08/11/2026).
    # decompressobj tolere un flux tronque par le Range.
    if brut[:2] == b"\x1f\x8b":
        brut = zlib.decompressobj(31).decompress(brut, 5 * 1024 * 1024)
    return brut.decode("utf-8", "replace")


def _synthese(eps, dates):
    """Frequence = ecart MEDIAN, pas moyen : une reprise apres six mois de
    pause fausserait completement une moyenne."""
    freq = None
    dates = sorted([d for d in dates if d], reverse=True)
    if len(dates) >= 3:
        ecarts = sorted((dates[i] - dates[i + 1]).days for i in range(len(dates) - 1))
        ecarts = [e for e in ecarts if e >= 0]
        if ecarts:
            freq = ecarts[len(ecarts) // 2]
    derniere = dates[0].date().isoformat() if dates else None
    # Certains flux ne listent pas dans l'ordre chronologique
    # (« 1&1 Font Casts » sortait juin 2024 avant avril 2024).
    eps = sorted(eps, key=lambda e: e.get("date") or "", reverse=True)
    return eps[:MAX_EPISODES], derniere, freq


def episodes_podcast(feed_url):
    x = _lire(feed_url)
    eps, dates = [], []
    for it in re.findall(r"<item[ >](.*?)</item>", x, re.S)[:12]:
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
        titre = _texte(t.group(1))[:110] if t else None
        dt = None
        if d:
            try:
                dt = parsedate_to_datetime(d.group(1).strip())
            except Exception:
                dt = None
        if titre:
            eps.append({"titre": titre, "date": dt.date().isoformat() if dt else None})
        if dt:
            dates.append(dt)
    return _synthese(eps, dates)


def episodes_youtube(channel_id):
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id
    x = _lire(url, ko=60)
    eps, dates = [], []
    for e in re.findall(r"<entry>(.*?)</entry>", x, re.S)[:12]:
        t = re.search(r"<media:title>(.*?)</media:title>", e, re.S)
        d = re.search(r"<published>(.*?)</published>", e)
        titre = _texte(t.group(1))[:110] if t else None
        dt = None
        if d:
            try:
                dt = datetime.fromisoformat(d.group(1).strip().replace("Z", "+00:00"))
            except Exception:
                dt = None
        if titre:
            eps.append({"titre": titre, "date": dt.date().isoformat() if dt else None})
        if dt:
            dates.append(dt)
    return _synthese(eps, dates)


def audience(d):
    pf = d.get("platforms") or {}
    return max((pf.get("apple") or {}).get("ratingCount") or 0,
               ((pf.get("youtube") or {}).get("subscribers") or 0) / 1000)


def intervalle(d, tete, aujourdhui):
    """Jours entre deux relectures d'une fiche deja remplie."""
    if d["slug"] in tete or d.get("mediacritic"):
        return INTERVALLE_TETE
    derniere = d.get("derniere_activite") or ""
    if derniere >= (aujourdhui - timedelta(days=60)).isoformat():
        return INTERVALLE_ACTIF
    if derniere and derniere < (aujourdhui - timedelta(days=365)).isoformat():
        return INTERVALLE_DORMANT
    return INTERVALLE_AUTRE


def enrich(limit=300, dry_run=False):
    """Depuis le 08/11/2026 : ROTATION PERMANENTE. Avant, une fiche deja remplie
    n'etait plus jamais relue : 144 fiches sur 8 892 avaient un episode de
    moins de 14 jours, et les « derniers episodes » affiches vieillissaient
    indefiniment. Etat : « ok:AAAA-MM-JJ » = lue ce jour-la ; « ok » (ancien
    format) = date inconnue, donc a relire en priorite ; « AAAA-MM-JJ » =
    echec, a retenter apres RETENTER_APRES jours."""
    etat = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    feeds = json.loads(FEEDS.read_text(encoding="utf-8")) if FEEDS.exists() else {}
    aujourdhui = date.today()
    seuil = (aujourdhui - timedelta(days=RETENTER_APRES)).isoformat()

    fiches = []
    for f in sorted(glob.glob(str(DATA / "*.json"))):
        try:
            d = json.loads(open(f, encoding="utf-8-sig").read())
        except Exception:
            continue
        if d.get("slug"):
            fiches.append((Path(f), d))
    tete = {d["slug"] for _, d in sorted(fiches, key=lambda x: -audience(x[1]))[:TAILLE_TETE]}

    nouvelles, dues = [], []
    for path, d in fiches:
        slug = d["slug"]
        pf = d.get("platforms") or {}
        cid = (pf.get("youtube") or {}).get("channelId")
        tid = (pf.get("apple") or {}).get("trackId")
        if not (cid or tid):
            continue
        marque = etat.get(slug) or ""
        if not d.get("episodes_recents"):
            # Jamais remplie : prioritaire, sauf echec recent.
            if not (marque[:2].isdigit() and marque > seuil):
                nouvelles.append((path, d, cid, tid))
            continue
        lue = marque[3:] if marque.startswith("ok:") else ""
        limite = (aujourdhui - timedelta(days=intervalle(d, tete, aujourdhui))).isoformat()
        if lue <= limite:
            # Les plus en retard d'abord ; a retard egal, les plus suivies.
            dues.append((lue, -audience(d), path, d, cid, tid))
    # Tete et emissions critiquees d'abord : ce sont les fiches les plus vues.
    dues.sort(key=lambda x: (not (x[3]["slug"] in tete or x[3].get("mediacritic")), x[0], x[1]))
    cibles = (nouvelles + [(p_, d_, c_, t_) for _, _, p_, d_, c_, t_ in dues])[:limit]

    if not cibles:
        print("  episodes : rien a relire")
        return 0

    manquants = {}
    for _, d, c, t in cibles:
        if t and not c and d["slug"] not in feeds:
            manquants[int(t)] = d["slug"]
    if manquants:
        ids = list(manquants)
        for i in range(0, len(ids), 100):
            url = ("https://itunes.apple.com/lookup?country=fr&id="
                   + ",".join(str(x) for x in ids[i:i + 100]))
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
                for res in data.get("results", []):
                    tid = res.get("collectionId") or res.get("trackId")
                    if tid in manquants:
                        feeds[manquants[tid]] = res.get("feedUrl") or ""
            except Exception as e:
                print("    lookup lot %d : %s" % (i // 100 + 1, e))
            time.sleep(0.2)
        for slug in manquants.values():
            feeds.setdefault(slug, "")
        if not dry_run:
            FEEDS.write_text(json.dumps(feeds, ensure_ascii=False), encoding="utf-8")

    def traiter(item):
        path, d, cid, tid = item
        try:
            if cid:
                return path, d, episodes_youtube(cid)
            u = feeds.get(d["slug"])
            if not u:
                return path, d, None
            return path, d, episodes_podcast(u)
        except Exception:
            return path, d, None

    remplies = vides = inchangees = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(traiter, c) for c in cibles]
        for fu in as_completed(futs):
            path, d, res = fu.result()
            if not res or not res[0]:
                vides += 1
                # Une fiche deja remplie garde ses episodes : flux muet n'efface
                # rien, et elle sera relue au prochain tour de son intervalle.
                etat[d["slug"]] = (("ok:" + aujourdhui.isoformat()) if d.get("episodes_recents")
                                   else aujourdhui.isoformat())
                continue
            eps, derniere, freq = res
            etat[d["slug"]] = "ok:" + aujourdhui.isoformat()
            # Reecrire seulement si quelque chose a change : la date du sitemap
            # ne doit bouger que pour de vraies nouveautes.
            if (d.get("episodes_recents") == eps and d.get("derniere_activite") == derniere
                    and d.get("frequence_jours") == freq):
                inchangees += 1
                continue
            remplies += 1
            if not dry_run:
                d["episodes_recents"] = eps
                if derniere:
                    d["derniere_activite"] = derniere
                if freq is not None:
                    d["frequence_jours"] = freq
                path.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    if not dry_run:
        ETAT.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")
    suffixe = " (simulation)" if dry_run else ""
    print("  episodes : %d fiche(s) relue(s) : %d mise(s) à jour, %d inchangée(s), %d sans flux%s"
          % (len(cibles), remplies, inchangees, vides, suffixe))
    return remplies


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    enrich(limit=a.limit, dry_run=a.dry_run)
