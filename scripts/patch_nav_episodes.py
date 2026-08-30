#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ajoute Annuaire / Classement / Comparateur a la nav d'une page episode.

Les 42 pages episodes ne pointaient que vers l'accueil et le palmares : ni vers
l'annuaire, ni vers le classement, ni vers le comparateur. Les pages les plus
lues du site ignoraient les trois pages qui portent l'identite d'annuaire.

Le gabarit templates/episode.html porte desormais ces liens, donc les episodes
futurs les auront d'office. Ce script sert au rattrapage des pages deja
publiees, et reste idempotent : une page deja a jour n'est pas retouchee.

Usage : python scripts/patch_nav_episodes.py episodes/*.html templates/episode.html
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

TROPHEE = "\U0001f3c6"
LIENS = (
    '<a href="../catalogue.html" class="nav-back">Annuaire</a>\n'
    '    <a href="../classement.html" class="nav-back">Classement</a>\n'
    '    <a href="../comparer.html" class="nav-back">Comparateur</a>\n'
)

# Nav courante : le lien Palmares dore sert d'ancre.
PALMARES = ('<a href="../palmares.html" class="nav-back" '
            'style="color:var(--c-gold)">' + TROPHEE + ' Palmarès</a>')

# Trois pages anciennes (tech-45, naufrages-une-histoire-vraie,
# l-entretien-geopolitique) n'ont jamais eu ce lien dans leur nav : on
# s'accroche alors a la marque, presente sur toutes les variantes.
MARQUE = '<span class="nav-brand">MediaCritic</span>'


def sans_total(txt):
    """« Épisode 10 / 23 » -> « Épisode 10 ».

    Le total etait fige a la date de publication de chaque page : 21 pages
    annonçaient 23 episodes, une 24, une 25, alors qu'il y en a 43. Un total
    ecrit en dur derive chaque semaine -- le corriger ne ferait que repousser
    le probleme d'une publication. Les pages recentes ne l'affichent deja
    plus : on s'aligne sur elles."""
    return re.sub(r"(Épisode\s+\d+)\s*/\s*\d+", "\g<1>", txt)


def patch(txt):
    """Renvoie (texte, etat) ou etat vaut True (modifie), False (deja a jour)
    ou None (nav non reconnue -- on ne touche a rien plutot que de casser)."""
    txt2 = sans_total(txt)
    if "../classement.html" in txt2:
        return txt2, (txt2 != txt)
    txt = txt2
    if PALMARES in txt:
        return txt.replace(PALMARES, LIENS + "    " + PALMARES, 1), True
    if MARQUE in txt:
        return txt.replace(MARQUE, MARQUE + "\n    " + LIENS + "    " + PALMARES, 1), True
    return txt, None


def main():
    faits = deja = rates = 0
    # Sans argument : toutes les pages episodes + le gabarit. C'est ce qui
    # permet de l'appeler apres chaque publication sans rien lui passer.
    cibles = [Path(a) for a in sys.argv[1:]] or (
        sorted((ROOT / "episodes").glob("*.html")) + [ROOT / "templates" / "episode.html"])
    for f in cibles:
        out, etat = patch(f.read_text(encoding="utf-8"))
        if etat is None:
            rates += 1
            print(f"  ! nav non reconnue, ignoré : {f.name}")
        elif etat:
            f.write_text(out, encoding="utf-8")
            faits += 1
        else:
            deja += 1
    print(f"{faits} page(s) mise(s) à jour, {deja} déjà à jour, {rates} ignorée(s)")


if __name__ == "__main__":
    main()
