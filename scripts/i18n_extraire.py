#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Site en anglais, livraison B (23/11/2026) : liste les paragraphes
editoriaux d'une page qui n'ont pas encore de traduction, pour preparer
i18n/en/pages/<page>.json ({texte francais: HTML anglais}).

Meme cle que assets/i18n.js (cleBloc) : textContent du bloc, espaces
reduits. Les blocs deja couverts par i18n/en.json (textes exacts, blocs
globaux) ou par le fichier de la page sont ignores, comme l'en-tete, le
pied de page, les scripts et les noms d'emissions.

Usage : python scripts/i18n_extraire.py page.html [...]  -> JSON sur stdout
        python scripts/i18n_extraire.py --enregistrer page.html  (met a jour
        la liste « pages » de i18n/en.json une fois le fichier ecrit)
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
EN = ROOT / "i18n" / "en.json"
BLOCS = r"p|li|h1|h2|h3|h4|blockquote|td|dd|dt|figcaption|summary"


def cle(inner):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", inner)).split())


def blocs_de(path):
    t = Path(path).read_text(encoding="utf-8")
    t = re.sub(r"<!-- mc-header -->.*?<!-- /mc-header -->", "", t, flags=re.S)
    t = re.sub(r"<!-- mc-footer -->.*?<!-- /mc-footer -->", "", t, flags=re.S)
    t = re.sub(r"<(script|style|template)\b.*?</\1>", "", t, flags=re.S)
    out = {}
    for m in re.finditer(r"<(%s)\b[^>]*>(.*?)</\1>" % BLOCS, t, re.S):
        inner = m.group(2)
        if re.search(r"<(p|li|ul|ol|div|h\d|section|article|img)\b", inner) or 'class="top-' in inner \
                or 'class="cl-' in inner or 'class="card' in inner:
            continue
        k = cle(inner)
        if len(k) > 2 and re.search(r"[A-Za-zÀ-ÿ]{3}", k):
            out[k] = inner.strip()
    return out


def main():
    args = sys.argv[1:]
    if args and args[0] == "--enregistrer":
        d = json.loads(EN.read_text(encoding="utf-8"))
        pages = set(d.get("pages") or [])
        for p in args[1:]:
            if (ROOT / "i18n" / "en" / "pages" / (p + ".json")).exists():
                pages.add(p)
        d["pages"] = sorted(pages)
        EN.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(pages)} page(s) avec traduction")
        return
    d = json.loads(EN.read_text(encoding="utf-8"))
    connus = set(d.get("textes") or {}) | set(d.get("blocs") or {})
    regles = [re.compile(r) for r, _ in d.get("regles") or []]
    res = {}
    for p in args:
        f = ROOT / "i18n" / "en" / "pages" / (p + ".json")
        deja = set(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else set()
        res[p] = {k: v for k, v in blocs_de(ROOT / p).items()
                  if k not in connus and k not in deja and not any(r.search(k) for r in regles)}
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
