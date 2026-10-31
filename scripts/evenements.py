# -*- coding: utf-8 -*-
"""
Calendrier d'evenements du podcast du jour (choix de l'utilisateur,
31/10/2026) : PRIORITAIRE sur l'actu, sauf actu exceptionnelle (voir
du_jour.py, EXCEPTION_*). Fichier interne : scripts/ n'est pas publie.

Chaque evenement : nom affiche, mots cherches dans les titres d'episodes,
periode (debut, fin incluses) et jour J (pour la phrase « c'est aujourd'hui »).
Le lien direct reste exige : un episode recent doit nommer l'evenement.
"""
from datetime import date, timedelta


def _paques(annee):
    """Dimanche de Paques (algorithme de Meeus)."""
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mois = (h + l_ - 7 * m + 114) // 31
    jour = ((h + l_ - 7 * m + 114) % 31) + 1
    return date(annee, mois, jour)


def _nieme_jour(annee, mois, jour_semaine, n):
    """n-ieme jour_semaine (0 = lundi) du mois ; n = -1 : le dernier."""
    if n > 0:
        d = date(annee, mois, 1)
        d += timedelta(days=(jour_semaine - d.weekday()) % 7)
        return d + timedelta(weeks=n - 1)
    d = date(annee, mois + 1, 1) - timedelta(days=1) if mois < 12 else date(annee, 12, 31)
    return d - timedelta(days=(d.weekday() - jour_semaine) % 7)


def evenements(annee):
    """[(nom, mots, debut, fin, jour_j)]"""
    p = _paques(annee)
    fete_meres = _nieme_jour(annee, 5, 6, -1)          # dernier dimanche de mai
    if fete_meres == p + timedelta(days=49):          # Pentecote : 1er dimanche de juin
        fete_meres += timedelta(weeks=1)
    black_friday = _nieme_jour(annee, 11, 4, 4)
    beaujolais = _nieme_jour(annee, 11, 3, 3)
    J = lambda m, j: date(annee, m, j)
    return [
        ("Nouvel An", ["nouvel an", "reveillon", "bonne annee", "resolutions"], J(1, 1), J(1, 3), J(1, 1)),
        ("Épiphanie", ["galette des rois", "epiphanie"], J(1, 4), J(1, 10), J(1, 6)),
        ("Chandeleur", ["chandeleur", "crepes"], J(1, 30), J(2, 2), J(2, 2)),
        ("Saint-Valentin", ["saint valentin", "saint-valentin"], J(2, 8), J(2, 14), J(2, 14)),
        ("Mardi gras", ["mardi gras", "carnaval"], p - timedelta(days=50), p - timedelta(days=47), p - timedelta(days=47)),
        ("Journée des droits des femmes", ["8 mars", "droits des femmes"], J(3, 6), J(3, 8), J(3, 8)),
        ("Saint-Patrick", ["saint patrick", "saint-patrick"], J(3, 15), J(3, 17), J(3, 17)),
        ("Poisson d'avril", ["poisson d avril"], J(3, 30), J(4, 1), J(4, 1)),
        ("Pâques", ["paques", "chocolat de paques"], p - timedelta(days=6), p + timedelta(days=1), p),
        ("Fête du travail", ["1er mai", "fete du travail", "muguet"], J(4, 29), J(5, 1), J(5, 1)),
        ("Festival de Cannes", ["festival de cannes", "cannes", "palme d or"], J(5, 12), J(5, 24), J(5, 24)),
        ("Roland-Garros", ["roland garros", "roland-garros"], J(5, 24), J(6, 7), J(6, 7)),
        ("Fête des mères", ["fete des meres"], fete_meres - timedelta(days=6), fete_meres, fete_meres),
        ("Bac", ["bac", "baccalaureat"], J(6, 12), J(6, 18), J(6, 15)),
        ("Fête des pères", ["fete des peres"], _nieme_jour(annee, 6, 6, 3) - timedelta(days=6), _nieme_jour(annee, 6, 6, 3), _nieme_jour(annee, 6, 6, 3)),
        ("Fête de la musique", ["fete de la musique"], J(6, 18), J(6, 21), J(6, 21)),
        ("Tour de France", ["tour de france"], J(7, 1), J(7, 26), J(7, 26)),
        ("14 Juillet", ["14 juillet", "fete nationale", "feu d artifice"], J(7, 11), J(7, 14), J(7, 14)),
        ("Rentrée", ["rentree"], J(8, 28), J(9, 7), J(9, 1)),
        ("Journées du patrimoine", ["journees du patrimoine"], _nieme_jour(annee, 9, 5, 3) - timedelta(days=3), _nieme_jour(annee, 9, 5, 3) + timedelta(days=1), _nieme_jour(annee, 9, 5, 3)),
        ("Halloween", ["halloween"], J(10, 24), J(10, 31), J(10, 31)),
        ("Toussaint", ["toussaint"], J(11, 1), J(11, 2), J(11, 1)),
        ("Armistice", ["11 novembre", "armistice"], J(11, 9), J(11, 11), J(11, 11)),
        ("Beaujolais nouveau", ["beaujolais"], beaujolais - timedelta(days=2), beaujolais, beaujolais),
        ("Black Friday", ["black friday"], black_friday - timedelta(days=5), black_friday, black_friday),
        ("Téléthon", ["telethon"], _nieme_jour(annee, 12, 4, 1) - timedelta(days=3), _nieme_jour(annee, 12, 4, 1) + timedelta(days=1), _nieme_jour(annee, 12, 4, 1)),
        ("Noël", ["noel", "sapin", "cadeaux de noel"], J(12, 10), J(12, 25), J(12, 25)),
        ("Réveillon du Nouvel An", ["reveillon", "nouvel an", "saint sylvestre"], J(12, 26), J(12, 31), J(12, 31)),
    ]


def du_jour(jour):
    """Evenements actifs ce jour-la, le plus proche de son jour J d'abord."""
    actifs = [e for e in evenements(jour.year) if e[2] <= jour <= e[3]]
    return sorted(actifs, key=lambda e: abs((e[4] - jour).days))


def quand(e, jour):
    """« c'est aujourd'hui », « c'est demain », « le 25 décembre »."""
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre"]
    d = (e[4] - jour).days
    if d == 0:
        return "c'est aujourd'hui"
    if d == 1:
        return "c'est demain"
    if d < 0:
        return "c'était il y a quelques jours"
    j = "1er" if e[4].day == 1 else str(e[4].day)
    return f"c'est le {j} {mois[e[4].month - 1]}"
