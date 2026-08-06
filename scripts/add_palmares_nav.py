#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ajoute le lien Palmarès à la nav des pages épisodes existantes.
Idempotent. Les futures pages l'ont déjà via templates/episode.html.

Usage : python scripts/add_palmares_nav.py
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent
OLD = '    <span class="nav-brand">MediaCritic</span>\n  </div>'
NEW = ('    <span class="nav-brand">MediaCritic</span>\n'
       '    <a href="../palmares.html" class="nav-back" style="color:var(--c-gold)">🏆 Palmarès</a>\n'
       '  </div>')

patched = skipped = 0
for p in sorted((ROOT / "episodes").glob("*.html")):
    html = p.read_text(encoding="utf-8")
    if "palmares.html" in html:
        skipped += 1
        continue
    if OLD not in html:
        print(f"  ! motif nav introuvable : {p.name}")
        continue
    p.write_text(html.replace(OLD, NEW, 1), encoding="utf-8")
    patched += 1

print(f"{patched} pages épisodes patchées, {skipped} déjà à jour.")
