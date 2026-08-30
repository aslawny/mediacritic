#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repare les fiches L'Equipe orphelines (HTML sans data/content).

Historique, retabli en lisant git plutot qu'en supposant :

  - Ep29 (24/05/2026) a CREE volontairement 6 fiches non-MC de L'Equipe,
    ajoutees a catalog.json et au sitemap. Mais leurs data/content/*.json
    n'ont jamais ete ecrits : le travail editait catalog.json directement.
  - Un passage ulterieur de generate_fiches.py a reconstruit catalog.json
    DEPUIS data/content/. Sans source, les 6 sont sorties du catalogue.
  - Restait 6 pages HTML orphelines, dans le sitemap, que plus aucun
    generateur ne touchait : ni nav, ni partage, ni contenus similaires.

Le correctif n'est donc PAS de les supprimer -- c'etait mon hypothese de
depart, et elle etait fausse -- mais de leur rendre leur source, pour
qu'elles redeviennent des fiches normales.

Exception : « Echappees, le podcast cyclisme de L'Equipe » n'existe plus sous
ce nom chez Apple. Le podcast cyclisme de L'Equipe s'appelle desormais
« L'Equipe du Tour » (trackId 1695114908), deja au catalogue sous le slug
l-equipe-du-tour. Cette fiche-la est un doublon perime : on applique la regle
du doublon (garder celle qui vit) et on retire page + URL du sitemap.

Usage : python scripts/repair_fiches_orphelines.py [--dry-run]
"""
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONTENT = ROOT / "data" / "content"
UA = {"User-Agent": "MediaCritic/1.0 (+https://www.mediacritic.fr)"}

# trackId verifie un par un sur artistName = L'Equipe. Les titres « Swing »,
# « Undercut » et « Echappees » sont generiques : sans ce controle d'editeur,
# on referencait un podcast de jazz ou de Formule 1 autrichienne.
A_RECREER = {
    "afrique-football-club": 1721171673,
    "l-equipe-de-greg": 1586633703,
    "l-equipe-du-soir": 1208152960,
    "swing-le-podcast-golf-de-l-equipe": 1338783651,
    "undercut-le-podcast-f1-de-l-equipe": 1801548336,
}
A_SUPPRIMER = {"echappees-le-podcast-cyclisme-de-l-equipe": "l-equipe-du-tour"}

CATS = {
    "afrique-football-club": (["football", "sport"], ["sport"]),
    "l-equipe-de-greg": (["sport"], ["sport"]),
    "l-equipe-du-soir": (["football", "sport"], ["sport"]),
    "swing-le-podcast-golf-de-l-equipe": (["golf", "sport"], ["sport"]),
    "undercut-le-podcast-f1-de-l-equipe": (["sport"], ["sport"]),
}


def lookup(track_id):
    u = "https://itunes.apple.com/lookup?country=fr&id=%d" % track_id
    d = json.loads(urllib.request.urlopen(
        urllib.request.Request(u, headers=UA), timeout=25).read())
    r = d.get("results") or []
    return r[0] if r else None


def main():
    sec = "--dry-run" in sys.argv
    faits, rates = [], []

    for slug, tid in A_RECREER.items():
        cible = CONTENT / ("%s.json" % slug)
        if cible.exists():
            print("  = %s : source deja presente" % slug)
            continue
        r = lookup(tid)
        # Aucune invention : sans reponse d'Apple, on ne fabrique pas de fiche.
        if not r or not r.get("trackName"):
            rates.append(slug)
            continue
        cats, tags = CATS.get(slug, (["sport"], ["sport"]))
        img = (r.get("artworkUrl600") or r.get("artworkUrl100") or "").replace(
            "100x100bb", "600x600bb")
        data = {
            "slug": slug,
            "title": r["trackName"],
            "author": r.get("artistName", ""),
            "type": "podcast",
            "categories": cats,
            "description": "",
            "image": img,
            "language": "fr",
            "platforms": {"apple": {
                "url": r.get("trackViewUrl", ""),
                "trackId": tid,
                "rating": None,
                "ratingCount": None,
                "episodeCount": r.get("trackCount"),
            }},
            "mediacritic": None,
            "tags": tags,
            "addedAt": "2026-05-24",      # date reelle de creation (Ep29)
            "updatedAt": date.today().isoformat(),
        }
        faits.append((slug, r["trackName"], r.get("artistName")))
        if not sec:
            cible.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        time.sleep(0.3)

    for slug, remplacant in A_SUPPRIMER.items():
        page = ROOT / "fiches" / ("%s.html" % slug)
        url = "https://www.mediacritic.fr/fiches/%s.html" % slug
        smap = ROOT / "sitemap.xml"
        s = smap.read_text(encoding="utf-8")
        present = page.exists() or url in s
        if not present:
            print("  = %s : deja retire" % slug)
            continue
        print("  - %s : doublon perime de %s -> page + sitemap" % (slug, remplacant))
        if not sec:
            if page.exists():
                page.unlink()
            s2 = re.sub(r"[ \t]*<url><loc>%s</loc>.*?</url>\n" % re.escape(url), "", s)
            if s2 != s:
                smap.write_text(s2, encoding="utf-8")

    for slug, titre, auteur in faits:
        print("  + %-38s %s (%s)" % (slug, titre[:36], auteur))
    print("\n%d source(s) recreee(s)%s" % (len(faits), "  [essai a blanc]" if sec else ""))
    if rates:
        print("%d sans reponse Apple, laissee(s) telle(s) quelle(s) : %s"
              % (len(rates), ", ".join(rates)))


if __name__ == "__main__":
    main()
