#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pose la balise du bouton « Partager » en tete de page sur toute page qui
ne l'a pas encore.

Les cinq generateurs et le gabarit d'episode portent deja la balise : les
pages qu'ils produisent l'ont d'office. Ce script sert au rattrapage des
pages deja publiees (episodes, pages ecrites a la main) et de filet de
securite si une page passe entre les mailles.

Idempotent. Sans argument, il balaie toutes les pages HTML du site.

Usage : python scripts/patch_partage_global.py [fichiers...]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BALISE = '<script defer src="/assets/partage.js"></script>'
BLOC = ("<!-- Bouton « Partager » en tete de page. Composant autonome : il lit\n"
        "     document.title et location.href, donc rien a regenerer quand un\n"
        "     titre change. Voir assets/partage.js. -->\n"
        + BALISE + "\n</body>")


def cibles_par_defaut():
    dossiers = ["*.html", "episodes/*.html", "categories/*.html", "fiches/*.html"]
    vus = []
    for motif in dossiers:
        vus.extend(sorted(ROOT.glob(motif)))
    vus.append(ROOT / "templates" / "episode.html")
    return [f for f in vus if f.exists()]


def patch(txt):
    if "partage.js" in txt:
        return txt, False
    if txt.count("</body>") != 1:
        return txt, None          # structure inattendue : on ne touche a rien
    return txt.replace("</body>", BLOC), True


def main():
    cibles = [Path(a) for a in sys.argv[1:]] or cibles_par_defaut()
    faits = deja = rates = 0
    for f in cibles:
        out, etat = patch(f.read_text(encoding="utf-8"))
        if etat is None:
            rates += 1
            print("  ! structure inattendue, ignoré : %s" % f.name)
        elif etat:
            f.write_text(out, encoding="utf-8")
            faits += 1
        else:
            deja += 1
    print("%d page(s) équipée(s), %d déjà à jour, %d ignorée(s)" % (faits, deja, rates))


if __name__ == "__main__":
    main()
