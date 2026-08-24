#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supprime les fiches en double du catalogue.

Le bot cree parfois deux fiches pour un meme contenu, avec des slugs
differents : le podcast s'est renomme (« 0 calorie Talk Show » devenu « Tout
simplement »), ou son titre a ete slugifie differemment selon la source
(« l-heure-du-crime » via le classement, « lheure-du-crime » via la fiche
MediaCritic). Resultat : deux pages pour un meme podcast, ce que Google traite
en contenu duplique, et un doublon visible sur la page d'accueil.

Le titre ne peut PAS servir de critere : « L'Heure du Crime », « L'heure du
crime : les archives de Jacques Pradel » et « Les collections de l'heure du
crime » sont trois emissions distinctes. Le signal fiable est l'identifiant
de plateforme -- trackId Apple ou channelId YouTube.

Regle de conservation, dans l'ordre :
  1. la fiche analysee par MediaCritic (regle posee par l'utilisateur) ;
  2. a defaut, la fiche la mieux renseignee (description la plus longue) ;
  3. a defaut, la plus recemment mise a jour, puis le slug le plus court.

Les slugs supprimes rejoignent data/blocklist.json, sinon le bot les recree.

Usage :
  python scripts/dedupe_catalogue.py --dry-run
  python scripts/dedupe_catalogue.py
"""
import argparse, glob, json, os, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"


def identite(d):
    """Identifiant de plateforme, seul critere fiable pour un doublon."""
    p = d.get("platforms") or {}
    tid = (p.get("apple") or {}).get("trackId")
    if tid:
        return ("apple", int(tid))
    cid = (p.get("youtube") or {}).get("channelId")
    if cid:
        return ("youtube", str(cid))
    return None


def rang_conservation(item):
    """Plus la cle est petite, plus la fiche merite d'etre conservee."""
    path, d = item
    return (0 if d.get("mediacritic") else 1,
            -len((d.get("description") or "").strip()),
            (d.get("updatedAt") or ""),
            len(d.get("slug") or ""))


def nettoyer_sitemap(slugs):
    p = ROOT / "sitemap.xml"
    if not p.exists() or not slugs:
        return 0
    lignes = p.read_text(encoding="utf-8").splitlines(keepends=True)
    cibles = {f"<loc>{BASE}/fiches/{s}.html</loc>" for s in slugs}
    gardees = [l for l in lignes if not any(c in l for c in cibles)]
    p.write_text("".join(gardees), encoding="utf-8")
    return len(lignes) - len(gardees)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    groupes = defaultdict(list)
    total = 0
    for f in sorted(glob.glob(str(ROOT / "data" / "content" / "*.json"))):
        try:
            d = json.loads(open(f, encoding="utf-8-sig").read())
        except Exception:
            continue
        if not d.get("slug"):
            continue
        total += 1
        ident = identite(d)
        if ident:
            groupes[ident].append((Path(f), d))

    a_supprimer, gardes_mc = [], 0
    for ident, items in groupes.items():
        if len(items) < 2:
            continue
        items.sort(key=rang_conservation)
        garde, doublons = items[0], items[1:]
        if garde[1].get("mediacritic"):
            gardes_mc += 1
        for path, d in doublons:
            a_supprimer.append((d["slug"], path, garde[1]["slug"],
                                bool(d.get("mediacritic"))))

    perdrait_mc = [x for x in a_supprimer if x[3]]
    assert not perdrait_mc, f"refus : supprimerait une fiche MediaCritic {perdrait_mc}"

    print(f"  {total} fiches, {sum(1 for v in groupes.values() if len(v) > 1)} groupe(s) en double")
    print(f"  {len(a_supprimer)} fiche(s) en trop")
    print(f"  {gardes_mc} groupe(s) ou la fiche MediaCritic est conservee")

    if args.dry_run:
        for slug, _, garde, _ in sorted(a_supprimer)[:15]:
            print(f"    supprime {slug[:44]:46} -> garde {garde}")
        print("\n  (--dry-run : rien n'a ete supprime)")
        return

    slugs = []
    for slug, path, _, _ in a_supprimer:
        path.unlink(missing_ok=True)
        (ROOT / "fiches" / f"{slug}.html").unlink(missing_ok=True)
        slugs.append(slug)
    n = nettoyer_sitemap(slugs)

    bl_path = ROOT / "data" / "blocklist.json"
    bl = json.loads(bl_path.read_text(encoding="utf-8")) if bl_path.exists() else []
    avant = len(bl)
    bl = sorted(set(bl) | set(slugs))
    bl_path.write_text(json.dumps(bl, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    print(f"\n  {len(slugs)} fiche(s) supprimee(s), {n} URL(s) retiree(s) du sitemap")
    print(f"  blocklist : {avant} -> {len(bl)} slugs")
    print("  -> relancer generate_fiches.py, generate_categories.py, generate_palmares.py")


if __name__ == "__main__":
    main()
