#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pose le label « Podcast indépendant » en tete des pages episodes dont le
sujet est un podcast independant (demande de l'utilisateur, 25/10/2026).

Le label se place juste apres la pastille « Episode N — Saison S ». La
decision vient de scripts/independance.py, comme le guide et les fiches :
une seule definition. Idempotent : le bloc balise est retire puis repose,
donc un podcast qui cesserait d'etre classe independant perd son label.

Usage : python scripts/patch_indep_episodes.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from independance import INFOBULLE, est_independant, libelle  # noqa: E402  source unique

ROOT = Path(__file__).parent.parent
DEBUT, FIN = "<!-- mc-indep -->", "<!-- /mc-indep -->"
def label(item):
    return (DEBUT + '<a class="mc-indep mc-indep-lg mc-indep-ep" href="../podcasts-independants.html" '
            f'title="{INFOBULLE}">{libelle(item)}</a>' + FIN)
# Apres la pastille d'episode, et apres « Nouveau » s'il est la.
ANCRE = re.compile(r'(<div class="ep-num-badge">[^<]*</div>(?:<span class="ep-new-badge">[^<]*</span>)?)')


def main():
    revues = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
    modifiees = poses = 0
    for r in revues.values():
        page, slug = r.get("page"), r.get("slug")
        if not page or not slug:
            continue
        chemin = ROOT / "episodes" / page
        fiche = ROOT / "data" / "content" / f"{slug}.json"
        if not chemin.exists() or not fiche.exists():
            continue
        donnees = json.loads(fiche.read_text(encoding="utf-8"))
        indep = est_independant(donnees)
        html = chemin.read_text(encoding="utf-8")
        neuf = re.sub(re.escape(DEBUT) + ".*?" + re.escape(FIN), "", html, flags=re.S)
        if indep:
            neuf, n = ANCRE.subn(lambda m: m.group(1) + label(donnees), neuf, count=1)
            if not n:
                print(f"  ! {page} : pastille d'episode introuvable, label non pose")
                continue
            poses += 1
        if neuf != html:
            chemin.write_text(neuf, encoding="utf-8")
            modifiees += 1
    print(f"Label indépendant : {poses} épisode(s) concerné(s), {modifiees} page(s) modifiée(s)")


if __name__ == "__main__":
    main()
