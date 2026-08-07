#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-catégorise le catalogue à partir des genres OFFICIELS Apple Podcasts.

Corrige la dérive historique : le bot assignait la catégorie de la requête de
recherche utilisée pour découvrir un podcast (d'où des podcasts de voyage
classés « true crime »). La source de vérité devient le genre Apple.

Règles :
- contenus analysés par MediaCritic → FUSION : catégories éditoriales d'abord,
  genres Apple en complément (rien n'est perdu), plafond MAX_MC ;
- autres contenus avec genre Apple → genres Apple ;
- chaînes YouTube / sans genre Apple → inchangés.

Usage :
  python scripts/recategorize.py --dry-run    # aperçu
  python scripts/recategorize.py              # applique
"""
import argparse, glob, json, os, sys, time, unicodedata, urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apple_genre_map import categories_from_apple

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "_apple_genres.json"
MAX_MC = 5


def fold(s):
    """« société » → « societe ». Les pages catégories (generate_categories.py)
    filtrent sur des formes sans accent : une catégorie accentuée n'y apparaît
    jamais. On normalise donc tout le catalogue sur cette forme."""
    s = unicodedata.normalize("NFD", str(s).strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm_list(cats):
    """Normalise et dédoublonne en conservant l'ordre."""
    out = []
    for c in cats or []:
        f = fold(c)
        if f and f not in out:
            out.append(f)
    return out


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def fetch_missing(fiches, cache):
    """Complète le cache des genres Apple par lots de 100 trackId."""
    todo = {}
    for slug, d in fiches.items():
        if slug in cache:
            continue
        tid = ((d.get("platforms") or {}).get("apple") or {}).get("trackId")
        if tid:
            todo[tid] = slug
    if not todo:
        return cache
    print(f"  {len(todo)} genres Apple à récupérer…")
    ids = list(todo)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        url = ("https://itunes.apple.com/lookup?country=fr&entity=podcast&id="
               + ",".join(str(x) for x in chunk))
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8", errors="replace"))
            for res in data.get("results", []):
                tid = res.get("collectionId") or res.get("trackId")
                if tid in todo:
                    cache[todo[tid]] = {"genres": res.get("genres") or []}
        except Exception as e:
            print(f"    lot {i//100+1}: {e}")
        for tid in chunk:
            cache.setdefault(todo[tid], {"genres": []})
        time.sleep(0.25)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache


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

    reviews = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
    mc_slugs = {r["slug"] for r in reviews.values()}

    cache = fetch_missing({s: d for s, (p, d) in fiches.items()}, load_cache())

    changed = kept = no_genre = 0
    for slug, (path, d) in fiches.items():
        before = d.get("categories") or []
        genres = (cache.get(slug) or {}).get("genres") or []
        apple = norm_list(categories_from_apple(genres)) if genres else []
        if not apple:
            # pas de genre Apple (chaînes YouTube surtout) : on se contente de
            # normaliser l'existant pour qu'il matche les pages catégories
            no_genre += 1
            after = norm_list(before)
        elif slug in mc_slugs:
            # fusion : éditorial d'abord, Apple en complément
            after = norm_list(before)
            for c in apple:
                if c not in after:
                    after.append(c)
            after = after[:MAX_MC]
        else:
            after = apple
        if after == before:
            kept += 1
            continue
        changed += 1
        if not args.dry_run:
            d["categories"] = after
            if not d.get("tags"):
                d["tags"] = after
            path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    verb = "seraient" if args.dry_run else "ont été"
    print(f"  {changed} fiches {verb} re-catégorisées")
    print(f"  {kept} déjà conformes")
    print(f"  {no_genre} sans genre Apple (accents normalisés uniquement)")
    print(f"  {len(mc_slugs)} contenus analysés : fusion éditorial + Apple (max {MAX_MC})")


if __name__ == "__main__":
    main()
