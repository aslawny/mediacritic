#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Met les metadonnees des pages episodes aux normes SEO.

Trois defauts constates sur les 43 pages :
  - 36 <title> depassaient 60 caracteres (jusqu'a 101), donc tronques par
    Google. Le gabarit concatene « MediaCritic Ép. N — Titre | Tagline » et le
    tagline, long sur les premiers episodes, faisait exploser la limite.
  - 14 meta descriptions depassaient 160 caracteres.
  - 43 pages sur 43 n'avaient pas de balise twitter:card : les partages sur X
    s'affichaient sans grande image.

Le gabarit templates/episode.html est corrige pour les episodes futurs ; ce
script rattrape les pages deja publiees. Idempotent, et sans argument il
traite tout episodes/.

⚠️ On ne touche jamais au nom du contenu analyse : c'est le mot-cle de la page.
Quand il faut raccourcir, c'est le tagline qui saute, jamais le titre.

Usage : python scripts/patch_meta_episodes.py [fichiers...]
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
LIMITE_TITRE = 60
LIMITE_DESC = 160

TWITTER = """<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@MediaCriticInc" />"""


def couper(txt, limite):
    """Tronque sur une frontiere de mot : couper au caractere pres produisait
    des fins de phrase absurdes dans les extraits Google."""
    txt = " ".join(txt.split())
    if len(txt) <= limite:
        return txt
    bout = txt[:limite - 1]
    esp = bout.rfind(" ")
    return (bout[:esp] if esp > limite * 0.6 else bout).rstrip(" ,;:—-") + "…"


def titre_court(brut):
    """« MediaCritic Ép. 39 — Naufragés… | In Extremis, le podcast… » (101 car.)
    devient « MediaCritic Ép. 39 — Naufragés — une histoire vraie » (50)."""
    if len(html.unescape(brut)) <= LIMITE_TITRE:
        return brut
    sans_tagline = brut.rsplit(" | ", 1)[0] if " | " in brut else brut
    if len(html.unescape(sans_tagline)) <= LIMITE_TITRE:
        return sans_tagline
    return html.escape(couper(html.unescape(sans_tagline), LIMITE_TITRE), quote=True)


def patch(txt):
    orig = txt

    m = re.search(r"<title>(.*?)</title>", txt, re.S)
    if m:
        nouveau = titre_court(m.group(1).strip())
        if nouveau != m.group(1).strip():
            txt = txt[:m.start(1)] + nouveau + txt[m.end(1):]

    # Description : la meta ET les variantes og:/twitter: doivent rester alignees.
    md = re.search(r'<meta name="description" content="([^"]*)"', txt)
    if md and len(html.unescape(md.group(1))) > LIMITE_DESC:
        court = html.escape(couper(html.unescape(md.group(1)), LIMITE_DESC), quote=True)
        ancien = md.group(1)
        txt = txt.replace('content="%s"' % ancien, 'content="%s"' % court)

    if 'name="twitter:card"' not in txt and "</head>" in txt:
        txt = txt.replace("</head>", TWITTER + "\n</head>", 1)

    return txt, txt != orig


def main():
    cibles = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "episodes").glob("*.html"))
    faits = 0
    for f in cibles:
        out, change = patch(f.read_text(encoding="utf-8"))
        if change:
            f.write_text(out, encoding="utf-8")
            faits += 1
    print("%d page(s) épisode mise(s) aux normes, %d déjà conforme(s)"
          % (faits, len(cibles) - faits))


if __name__ == "__main__":
    main()
