#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Source unique des compteurs du site.

Le probleme : les memes chiffres etaient ecrits en dur dans index.html et
catalogue.html, calcules dans classement.html et les pages categories, et
recopies a la main dans les descriptions de marque. Le bot ajoutant des
contenus chaque nuit, les valeurs figees derivaient : l'accueil annoncait
8 300+, le classement 8 400+, le fichier en contenait 8 442.

Ici, tout est calcule depuis les donnees, puis reecrit partout.

Deux conventions, volontairement differentes :
  - Le texte de marque arrondit AU CENTAINE INFERIEURE et suffixe « + ».
    « 8 300+ » reste vrai tant qu'on a entre 8 300 et 8 399 contenus, donc la
    phrase ne devient jamais mensongere entre deux passages du bot.
  - Les donnees structurees (JSON-LD `numberOfItems`) portent le compte EXACT :
    un moteur n'a pas a lire un arrondi.

Les remplacements sont ancres sur leur contexte (« ... podcasts »,
« id="stat-total" »...) et jamais sur un nombre nu : index.html contient
« 11 633 avis Apple » et catalogue.html « 5 871 fiches », qui ne doivent pas
bouger.

Usage : python scripts/sync_compteurs.py [--dry-run]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
FINE = " "          # espace fine insecable, separateur des milliers du site


def fmt(n):
    return f"{n:,}".replace(",", FINE)


def compter():
    cat = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    rev = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
    total = len(cat)
    return {
        "total": total,
        "arrondi": (total // 100) * 100,
        "podcasts": sum(1 for x in cat if x.get("type") != "youtube"),
        "chaines": sum(1 for x in cat if x.get("type") == "youtube"),
        # Episodes publies, hors-serie compris : c'est ce que compte « N épisodes ».
        "episodes": len(rev),
        # Episodes portant une note : un hors-serie n'en a pas.
        "analyses": sum(1 for v in rev.values() if v.get("note") is not None),
        # Contenus marques dans l'annuaire. Superieur au nombre d'analyses car
        # l'episode 29 couvre a lui seul 4 podcasts de L'Equipe.
        "contenus_notes": sum(1 for x in cat if x.get("mcEpisode")),
    }


def regles(c):
    a = fmt(c["arrondi"])
    return [
        # Un millier suivi de « podcasts » ou « contenus » : c'est toujours le
        # compteur du catalogue. Pas d'ancrage arriere sur « Plus de » -- une
        # balise <strong> s'intercale parfois et le faisait echouer
        # silencieusement, laissant un « 8 300 » perime dans le H1 du catalogue.
        # Sur ces deux pages, aucun autre nombre n'est suivi de ces deux mots :
        # « 11 633 avis » et « 5 871 fiches » ne bougent pas.
        (re.compile(r"\d{1,2}%s\d{3}(\+?)(?= (?:podcasts|contenus))" % FINE),
         lambda m: a + m.group(1)),
        # Compteur visible de l'accueil et du catalogue
        (re.compile(r'(?<=id="stat-total">)[^<]*'), a + "+"),
        # Compteur « contenus analysés » du catalogue. Le HTML servi affichait 43
        # (le nombre d'episodes) alors que le JS de la page calcule
        # `mcNote || mcEpisode`, soit 45. On aligne le statique sur le calcule :
        # un moteur qui n'execute pas le JS lisait un chiffre faux.
        (re.compile(r'(?<=id="stat-mc">)[^<]*'), str(c["contenus_notes"])),
    ]


def regle_json_ld(c):
    """`numberOfItems` du catalogue complet. ⚠️ A n'appliquer QUE sur
    catalogue.html : classement.html en contient quatre autres qui comptent les
    entrees de chaque classement (50, 50, 30, 45). Un essai a blanc les a
    sauves d'un ecrasement par le total du catalogue."""
    return (re.compile(r'(?<="numberOfItems": )\d+'), str(c["total"]))


def stat_par_libelle(txt, libelle, valeur):
    """Remplace le nombre d'une paire <div class="num">N</div> + <div class="lbl">…"""
    motif = re.compile(
        r'(<div class="num"[^>]*>)([^<]*)(</div>\s*<div class="lbl">%s)' % re.escape(libelle))
    return motif.subn(lambda m: m.group(1) + str(valeur) + m.group(3), txt)


def main():
    sec = "--dry-run" in sys.argv
    c = compter()
    print("  Vérité calculée :")
    print("    %s contenus (%s podcasts, %s chaînes) → texte de marque « %s+ »"
          % (fmt(c["total"]), fmt(c["podcasts"]), fmt(c["chaines"]), fmt(c["arrondi"])))
    print("    %d épisodes publiés, %d portant une note, %d contenus marqués"
          % (c["episodes"], c["analyses"], c["contenus_notes"]))
    print()

    total_modifs = 0
    # classement.html et les pages categories sont generees : leur generateur
    # calcule deja le total. On ne touche qu'aux deux pages ecrites a la main.
    for nom in ("index.html", "catalogue.html"):
        f = ROOT / nom
        if not f.exists():
            continue
        t = orig = f.read_text(encoding="utf-8")
        n = 0
        for motif, remplacement in regles(c):
            t, k = motif.subn(remplacement, t)
            n += k
        if nom == "catalogue.html":
            motif, rempl = regle_json_ld(c)
            t, k = motif.subn(rempl, t); n += k
        if nom == "index.html":
            t, k = stat_par_libelle(t, "épisodes publiés", c["episodes"]); n += k
        if t != orig:
            total_modifs += n
            if not sec:
                f.write_text(t, encoding="utf-8")
            print("  %-18s %d remplacement(s)" % (nom, n))
        else:
            print("  %-18s déjà à jour" % nom)

    print("\n%d remplacement(s)%s" % (total_modifs, "  [essai à blanc]" if sec else ""))


if __name__ == "__main__":
    main()
