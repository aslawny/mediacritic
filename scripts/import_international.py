#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Catalogue international (decision de l'utilisateur, 23/11/2026) : podcasts
en anglais, espagnol, allemand, italien et portugais, plafond 10 000.

ISOLE du catalogue francophone : donnees dans data/content_intl/ (jamais
data/content/), catalogue data/catalog-intl.json (generate_fiches_intl.py).
Purge linguistique, classements, categories, podcast du jour, Mystere et
compteurs continuent de ne lire QUE le catalogue francais.

Source : classements Apple par pays et par genre (RSS public, sans quota),
lus en rotation. Un contenu n'entre que si :
  - la langue DECLAREE dans son flux RSS fait partie des langues retenues
    (preuve positive : flux illisible = rejete, jamais accepte par defaut ;
    lecon du 16/11/2026, ou un filtre muet avait tout laisse passer) ;
  - il n'est pas deja au catalogue francais (meme trackId Apple) ;
  - le quota de sa langue n'est pas atteint (QUOTAS, total 10 000).
Les rejets sont memorises (data/_intl_state.json) 90 jours.

Reseau : urllib, puis curl en secours (le Python de la machine locale echoue
sur les certificats HTTPS).

Usage : python scripts/import_international.py [--max N] [--combinaisons N] [--dry-run]
"""
import argparse
import glob
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
INTL = DATA / "content_intl"
ETAT = DATA / "_intl_state.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Langue -> quota (total = plafond de 10 000 valide par l'utilisateur).
QUOTAS = {"en": 4000, "es": 1700, "de": 1500, "it": 1300, "pt": 1500}
PLAFOND = 10000
# Pays dont on lit les classements, par langue visee.
PAYS = {"en": ["us", "gb", "ca", "au", "ie"], "es": ["es", "mx", "ar", "co"],
        "de": ["de", "at", "ch"], "it": ["it"], "pt": ["br", "pt"]}
# Genres Apple -> categories du site (memes slugs que le catalogue francais).
GENRES = [
    (1311, ["actualite", "news"]), (1318, ["tech", "numerique"]),
    (1314, ["sciences", "vulgarisation"]), (1324, ["societe", "culture"]),
    (1316, ["sport"]), (1512, ["sante", "bien-etre"]), (1488, ["true crime", "societe"]),
    (1303, ["humour", "comedie"]), (1304, ["education"]), (1305, ["enfants", "famille"]),
    (1309, ["cinema", "series"]), (1310, ["musique", "culture"]), (1301, ["arts", "culture"]),
    (1321, ["business", "entrepreneuriat"]), (1487, ["histoire"]), (1502, ["loisirs"]),
]
RETENTER_APRES = 90
# Repli par identifiant de genre Apple (parents), si la fiche n'existe pas en
# France : les categories viennent TOUJOURS des genres du podcast, jamais du
# classement lu (le flux « par genre » d'Apple renvoie en partie le top general).
PARENTS = {gid: cats for gid, cats in GENRES}
PARENTS.update({1489: ["actualite", "news"], 1533: ["sciences", "vulgarisation"],
                1545: ["sport"], 1483: ["fiction", "culture"], 1314: ["spiritualite"],
                1511: ["societe", "politique"]})
sys.path.insert(0, str(Path(__file__).parent))
from apple_genre_map import categories_from_apple  # noqa: E402  libelles francais


def lire(url, binaire=False, ko=None, timeout=20):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read(ko * 1024) if ko else r.read()
    except Exception:
        try:
            cmd = ["curl", "-s", "-L", "--compressed", "--max-time", str(timeout), "-A", UA["User-Agent"]]
            if ko:
                cmd += ["-r", f"0-{ko * 1024}"]
            b = subprocess.run(cmd + [url], capture_output=True, timeout=timeout + 10).stdout
        except Exception:
            return b"" if binaire else ""
    return b if binaire else b.decode("utf-8", "replace")


def lire_json(url):
    t = lire(url)
    try:
        return json.loads(t)
    except Exception:
        return {}


def slugify(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:80]


def texte(s):
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<[^>]+>", " ", html.unescape(s))
    return " ".join(html.unescape(s).split())


def flux(feed_url):
    """(langue, description) lues dans l'en-tete du flux, ou (None, '')."""
    if not (feed_url or "").startswith("http"):
        return None, ""
    x = lire(feed_url, ko=96)
    tete = x.split("<item", 1)[0]
    m = re.search(r"<language>\s*([A-Za-z]{2})[^<]*</language>", tete)
    d = (re.search(r"<itunes:summary>(.*?)</itunes:summary>", tete, re.S)
         or re.search(r"<description>(.*?)</description>", tete, re.S))
    return (m.group(1).lower() if m else None), (texte(d.group(1))[:1500] if d else "")


def note_apple(track_id, pays):
    t = lire(f"https://podcasts.apple.com/{pays}/podcast/id{track_id}", timeout=15)
    m = re.search(r'"ratingValue":([0-9.]+),"reviewCount":([0-9]+)', t)
    if not m:
        return None, None
    rv, rc = float(m.group(1)), int(m.group(2))
    return (rv if rv > 0 else None), (rc if rc > 0 else None)


def charger(dossier):
    out = {}
    for p in glob.glob(str(dossier / "*.json")):
        try:
            out[Path(p).stem] = json.load(open(p, encoding="utf-8-sig"))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=400, help="nouveaux contenus par passage")
    ap.add_argument("--combinaisons", type=int, default=60, help="classements (pays x genre) lus par passage")
    ap.add_argument("--par-classement", type=int, default=25, help="nouveaux contenus au plus par classement")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    INTL.mkdir(parents=True, exist_ok=True)
    try:
        etat = json.loads(ETAT.read_text(encoding="utf-8"))
    except Exception:
        etat = {"idx": 0, "vus": {}}
    seuil = (date.today() - timedelta(days=RETENTER_APRES)).isoformat()
    etat["vus"] = {k: v for k, v in etat.get("vus", {}).items() if v[:10] >= seuil}

    fr = charger(DATA / "content")
    intl = charger(INTL)
    ids_fr = {str(((d.get("platforms") or {}).get("apple") or {}).get("trackId")) for d in fr.values()}
    ids_intl = {str(((d.get("platforms") or {}).get("apple") or {}).get("trackId")) for d in intl.values()}
    compte = {k: 0 for k in QUOTAS}
    for d in intl.values():
        if d.get("langue") in compte:
            compte[d["langue"]] += 1
    total = sum(compte.values())
    print(f"  international : {total} contenus ({compte}), plafond {PLAFOND}")
    if total >= PLAFOND:
        print("  plafond atteint : rien a importer")
        return

    # Genre par genre, tous les pays : chaque passage nourrit toutes les langues.
    combos = [(lg, pays, gid) for gid, _ in GENRES for lg, lp in PAYS.items() for pays in lp]
    ajoutes, lus = 0, 0
    for k in range(min(a.combinaisons, len(combos))):
        lg_vise, pays, gid = combos[(etat["idx"] + k) % len(combos)]
        if compte[lg_vise] >= QUOTAS[lg_vise]:
            continue
        feed = lire_json(f"https://itunes.apple.com/{pays}/rss/toppodcasts/limit=200/genre={gid}/json")
        entrees = (feed.get("feed") or {}).get("entry") or []
        ids, pris = [], 0
        for e in entrees:
            tid = ((e.get("id") or {}).get("attributes") or {}).get("im:id")
            if tid and tid not in ids_fr and tid not in ids_intl and tid not in etat["vus"]:
                ids.append(tid)
        lus += 1
        for i in range(0, len(ids), 100):
            lot = ",".join(ids[i:i + 100])
            res = lire_json(f"https://itunes.apple.com/lookup?country={pays}&id=" + lot)
            genres_fr = {str(x.get("collectionId")): x.get("genres") or []
                         for x in (lire_json("https://itunes.apple.com/lookup?country=fr&id=" + lot).get("results") or [])}
            for r in res.get("results") or []:
                tid = str(r.get("collectionId") or r.get("trackId") or "")
                if not tid or tid in ids_intl:
                    continue
                code, desc = flux(r.get("feedUrl"))
                if code not in QUOTAS:
                    etat["vus"][tid] = f"{date.today().isoformat()}:langue {code or 'illisible'}"
                    continue
                if compte[code] >= QUOTAS[code] or total >= PLAFOND:
                    continue
                nom = (r.get("collectionName") or "").strip()
                slug = slugify(nom)
                if not slug:
                    continue
                if slug in fr or slug in intl or (ROOT / "fiches" / f"{slug}.html").exists():
                    slug = f"{slug}-{code}"
                    if slug in fr or slug in intl or (ROOT / "fiches" / f"{slug}.html").exists():
                        etat["vus"][tid] = f"{date.today().isoformat()}:slug pris"
                        continue
                cats = categories_from_apple(genres_fr.get(tid))
                if not cats:
                    for g in r.get("genreIds") or []:
                        if int(g) in PARENTS:
                            cats = PARENTS[int(g)]
                            break
                cats = cats or ["culture"]
                note, avis = note_apple(tid, pays)
                img = r.get("artworkUrl600") or r.get("artworkUrl100") or ""
                d = {
                    "slug": slug, "title": nom, "author": (r.get("artistName") or "").strip(),
                    "type": "podcast", "categories": cats, "tags": cats,
                    "description": desc, "image": img, "langue": code, "language": code,
                    "pays": pays.upper(),
                    "platforms": {"apple": {
                        "url": (r.get("collectionViewUrl") or "").split("?")[0],
                        "trackId": int(tid), "rating": note, "ratingCount": avis,
                        "episodeCount": r.get("trackCount"), "feedUrl": r.get("feedUrl")}},
                    "mediacritic": None, "addedAt": date.today().isoformat(),
                    "updatedAt": date.today().isoformat(),
                }
                if not a.dry_run:
                    (INTL / f"{slug}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                intl[slug] = d
                ids_intl.add(tid)
                compte[code] += 1
                total += 1
                ajoutes += 1
                pris += 1
                print(f"    + [{code}] {nom[:60]} ({pays})")
                if ajoutes >= a.max or pris >= a.par_classement:
                    break
                time.sleep(0.1)
            if ajoutes >= a.max or pris >= a.par_classement:
                break
        if ajoutes >= a.max:
            break
    etat["idx"] = (etat["idx"] + lus) % len(combos)
    if not a.dry_run:
        ETAT.write_text(json.dumps(etat, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"  international : +{ajoutes} ({lus} classement(s) lu(s)), total {total} : {compte}")


if __name__ == "__main__":
    main()
