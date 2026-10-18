#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pose la charte (en-tete, pied de page, assets/mc.css) sur les pages qui
ne passent par aucun generateur : pages ecrites a la main, pages episodes
deja publiees, gabarit des episodes.

Les pages generees (fiches, categories, palmares, classement, comparateur)
recoivent la charte de leur generateur, qui appelle charte.appliquer().

Idempotent. Sans argument : toutes les pages concernees. Dans REGENERATEURS
de publish_episode.py, pour qu'un episode publie ait toujours la charte.

Usage : python scripts/patch_charte.py [fichiers...]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from charte import appliquer  # noqa: E402

# Page -> (rubrique active de l'en-tete, palette)
# Palette « b » : pages ou les anciennes variables muted/muted2 ont le sens
# inverse de l'accueil (voir assets/mc.css).
PAGES = {
    "index.html": (None, None),
    "catalogue.html": ("annuaire", None),
    "qui-sommes-nous.html": ("equipe", None),
    "contact.html": (None, None),
    "mentions-legales.html": (None, "b"),
    "fiche.html": ("annuaire", "b"),       # gabarit de secours (noindex)
    "templates/episode.html": ("palmares", "b"),
}


def cibles():
    for nom, reglage in PAGES.items():
        yield ROOT / nom, reglage
    for f in sorted((ROOT / "episodes").glob("*.html")):
        yield f, ("palmares", "b")


def reglage_de(f):
    rel = f.resolve().relative_to(ROOT.resolve()).as_posix()
    if rel in PAGES:
        return PAGES[rel]
    if rel.startswith("episodes/"):
        return ("palmares", "b")
    return None


def main():
    args = [Path(a) for a in sys.argv[1:]]
    liste = [(f, reglage_de(f)) for f in args] if args else list(cibles())
    faits = deja = rates = 0
    for f, reglage in liste:
        if not f.exists() or reglage is None:
            rates += 1
            print("  ! ignoré (inconnu ou absent) : %s" % f)
            continue
        txt = f.read_text(encoding="utf-8")
        out, etat = appliquer(txt, *reglage)
        if etat is None:
            rates += 1
            print("  ! en-tête ou pied de page non reconnu, page laissée telle quelle : %s" % f.name)
        elif etat:
            f.write_text(out, encoding="utf-8")
            faits += 1
        else:
            deja += 1
    print("%d page(s) mise(s) à la charte, %d déjà conforme(s), %d ignorée(s)" % (faits, deja, rates))
    if rates:
        sys.exit(1)


if __name__ == "__main__":
    main()
