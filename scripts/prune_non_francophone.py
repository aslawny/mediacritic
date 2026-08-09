#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retire du catalogue les contenus dont la langue declaree n'est PAS le francais.

Principe de prudence : on ne supprime que sur preuve. Un flux injoignable, sans
balise <language>, ou une chaine YouTube sans signal clair sont CONSERVES. Les
contenus analyses par MediaCritic ne sont jamais touches, quelle que soit leur
langue (THE FIRST TAKE est japonais et a toute sa place).

Le cache des langues (data/_feed_langs.json) est complete au besoin ; les flux
deja connus ne sont pas re-interroges.

Usage :
  python scripts/prune_non_francophone.py --dry-run   # rapport, aucune suppression
  python scripts/prune_non_francophone.py             # applique
"""
import argparse, glob, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lang_filter import (langue_du_flux, est_code_francophone,
                         ecriture_non_latine, texte_manifestement_francais)

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "_feed_langs.json"
BASE = "https://www.mediacritic.fr"


def charger_cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def completer_cache(fiches, cache):
    """Resout les feedUrl manquants puis lit la langue de chaque flux."""
    import time, urllib.request
    manquants = {}
    for slug, d in fiches.items():
        if slug in cache or d.get("type") == "youtube":
            continue
        tid = ((d.get("platforms") or {}).get("apple") or {}).get("trackId")
        if tid:
            manquants[int(tid)] = slug
    if not manquants:
        return cache

    print(f"  {len(manquants)} langues a resoudre…")
    feeds, ids = {}, list(manquants)
    for i in range(0, len(ids), 100):
        url = ("https://itunes.apple.com/lookup?country=fr&id="
               + ",".join(map(str, ids[i:i + 100])))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                for res in json.loads(r.read().decode("utf-8", "replace")).get("results", []):
                    tid = res.get("collectionId") or res.get("trackId")
                    if tid in manquants and res.get("feedUrl"):
                        feeds[manquants[tid]] = res["feedUrl"]
        except Exception as e:
            print(f"    lookup lot {i//100+1} : {e}")
        time.sleep(0.2)

    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(langue_du_flux, u): s for s, u in feeds.items()}
        for fu in as_completed(futs):
            cache[futs[fu]] = fu.result() or "?"
    for slug in manquants.values():
        cache.setdefault(slug, "?")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache


def nettoyer_sitemap(slugs):
    """Retire les URLs des fiches supprimees (le generateur ajoute, il ne retire pas)."""
    p = ROOT / "sitemap.xml"
    if not p.exists() or not slugs:
        return 0
    lignes = p.read_text(encoding="utf-8").splitlines(keepends=True)
    cibles = {f"{BASE}/fiches/{s}.html" for s in slugs}
    gardees = [l for l in lignes
               if not any(f"<loc>{c}</loc>" in l for c in cibles)]
    p.write_text("".join(gardees), encoding="utf-8")
    return len(lignes) - len(gardees)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fiches = {}
    for f in glob.glob(str(ROOT / "data" / "content" / "*.json")):
        try:
            d = json.loads(open(f, encoding="utf-8-sig").read())
        except Exception:
            continue
        if d.get("slug"):
            fiches[d["slug"]] = (Path(f), d)

    cache = completer_cache({s: d for s, (p, d) in fiches.items()}, charger_cache())

    a_supprimer = []
    conserves = {"mc": 0, "fr": 0, "inconnu": 0, "youtube": 0, "rattrape": 0}
    for slug, (path, d) in fiches.items():
        if d.get("mediacritic"):
            conserves["mc"] += 1
            continue

        titre = f"{d.get('title', '')} {d.get('author', '')}"

        # Filet AVANT tout autre test : des podcasts francais portent un
        # sous-titre en alphabet etranger, et certains flux declarent mal leur
        # langue. Un texte manifestement francais prime sur les deux signaux.
        if texte_manifestement_francais(titre, d.get("description")):
            conserves["rattrape"] += 1
            continue

        if ecriture_non_latine(titre):
            a_supprimer.append((slug, path, "ecriture non latine"))
            continue

        if d.get("type") == "youtube":
            conserves["youtube"] += 1
            continue

        verdict = est_code_francophone(cache.get(slug))
        if verdict is False:
            a_supprimer.append((slug, path, cache.get(slug)))
        elif verdict is True:
            conserves["fr"] += 1
        else:
            conserves["inconnu"] += 1

    print(f"\n  {len(fiches)} fiches examinees")
    print(f"  conserves : {conserves['fr']} francophones, {conserves['inconnu']} langue inconnue,")
    print(f"              {conserves['youtube']} chaines YouTube, {conserves['mc']} analysees MC,")
    print(f"              {conserves['rattrape']} rattrapees (flux mal declare)")
    print(f"  a retirer : {len(a_supprimer)}")

    if args.dry_run:
        print("\n  (--dry-run : rien n'a ete supprime)")
        return

    slugs = []
    for slug, path, motif in a_supprimer:
        path.unlink(missing_ok=True)
        (ROOT / "fiches" / f"{slug}.html").unlink(missing_ok=True)
        slugs.append(slug)
    n = nettoyer_sitemap(slugs)

    # Sans cette etape, le bot les re-importerait des la nuit suivante : c'est
    # elle qui rend la suppression definitive.
    bl_path = ROOT / "data" / "blocklist.json"
    bl = json.loads(bl_path.read_text(encoding="utf-8")) if bl_path.exists() else []
    avant = len(bl)
    bl = sorted(set(bl) | set(slugs))
    bl_path.write_text(json.dumps(bl, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    print(f"\n  {len(slugs)} fiches supprimees, {n} URLs retirees du sitemap")
    print(f"  blocklist : {avant} -> {len(bl)} slugs (ne seront jamais recrees)")
    print("  -> relancer generate_fiches.py, generate_categories.py, generate_palmares.py")


if __name__ == "__main__":
    main()
