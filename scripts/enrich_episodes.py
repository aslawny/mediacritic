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


def _texte(x):
    x = re.sub(r"<!\[CDATA\[|\]\]>", "", x or "")
    x = re.sub(r"<[^>]+>", "", x)
    for _ in range(2):
        x = _html.unescape(x)
    return re.sub(r"\s+", " ", x).strip()


def _lire(url, ko=140, timeout=25):
    req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-%d" % (ko * 1024)})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(ko * 1024 + 1).decode("utf-8", "replace")


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


def enrich(limit=300, dry_run=False):
    etat = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    feeds = json.loads(FEEDS.read_text(encoding="utf-8")) if FEEDS.exists() else {}
    seuil = (date.today() - timedelta(days=RETENTER_APRES)).isoformat()

    cibles = []
    for f in sorted(glob.glob(str(DATA / "*.json"))):
        try:
            d = json.loads(open(f, encoding="utf-8-sig").read())
        except Exception:
            continue
        slug = d.get("slug")
        if not slug or d.get("episodes_recents"):
            continue
        marque = etat.get(slug)
        if marque and marque > seuil:
            continue
        pf = d.get("platforms") or {}
        cid = (pf.get("youtube") or {}).get("channelId")
        tid = (pf.get("apple") or {}).get("trackId")
        if cid or tid:
            cibles.append((Path(f), d, cid, tid))
        if len(cibles) >= limit:
            break

    if not cibles:
        print("  episodes : rien a completer")
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

    remplies = vides = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(traiter, c) for c in cibles]
        for fu in as_completed(futs):
            path, d, res = fu.result()
            if not res or not res[0]:
                vides += 1
                etat[d["slug"]] = date.today().isoformat()
                continue
            eps, derniere, freq = res
            remplies += 1
            etat[d["slug"]] = "ok"
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
    print("  episodes : %d fiche(s) enrichie(s), %d sans flux exploitable%s"
          % (remplies, vides, suffixe))
    return remplies


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    enrich(limit=a.limit, dry_run=a.dry_run)
