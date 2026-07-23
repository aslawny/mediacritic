#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ajoute un menu burger mobile aux pages dont la nav (.nav-links) disparaît
sous 640px sans alternative. Idempotent : détecte le marqueur nav-burger.

Usage : python scripts/add_mobile_menu.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

BURGER_CSS = """<style>/* mc-burger : menu mobile */
.nav-burger{display:none;background:none;border:1px solid rgba(255,255,255,.15);color:inherit;font-size:1.05rem;line-height:1;padding:6px 11px;border-radius:8px;cursor:pointer}
@media(max-width:640px){
.nav-burger{display:block}
.nav-links{display:none;position:absolute;top:100%;left:0;right:0;background:rgba(6,11,20,.98);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.08);flex-direction:column;align-items:stretch;padding:10px 16px 14px;gap:4px;z-index:400}
.nav-links.open{display:flex}
.nav-links a{padding:10px 12px;font-size:.92rem}
}</style>"""

BURGER_BTN = ('<button class="nav-burger" aria-label="Ouvrir le menu" aria-expanded="false" '
              'onclick="var l=document.querySelector(\'.nav-links\');l.classList.toggle(\'open\');'
              'this.setAttribute(\'aria-expanded\',l.classList.contains(\'open\'));">☰</button>')

TARGETS = (
    [ROOT / f for f in ("index.html", "catalogue.html", "qui-sommes-nous.html",
                        "contact.html", "palmares.html")]
    + sorted((ROOT / "categories").glob("*.html"))
)

patched = skipped = 0
for path in TARGETS:
    if not path.exists():
        print(f"  ! absent : {path.name}")
        continue
    content = path.read_text(encoding="utf-8")
    if "nav-burger" in content:
        skipped += 1
        continue
    if '<div class="nav-links">' not in content:
        print(f"  ! pas de nav-links : {path.name}")
        continue
    content = content.replace('<div class="nav-links">',
                              BURGER_BTN + '\n<div class="nav-links">', 1)
    content = content.replace("</head>", BURGER_CSS + "\n</head>", 1)
    path.write_text(content, encoding="utf-8")
    patched += 1
    print(f"  burger ajouté : {path.relative_to(ROOT)}")

print(f"\n{patched} pages patchées, {skipped} déjà à jour.")
