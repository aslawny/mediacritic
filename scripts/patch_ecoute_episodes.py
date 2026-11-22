#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lecteur du site sur NOS pages episodes (21/11/2026) : boutons « ▶ Écouter »
et « + Ma liste » dans la rangee de boutons de chaque episode MediaCritic.

Source : notre propre flux RSS (Ausha), episodes titres « S02-Ep54 … » ->
numero -> page (data/mc_reviews.json). Idempotent (marqueurs) ; dans
REGENERATEURS de publish_episode.py et dans la boucle d'enrich.yml, donc
chaque nouvel episode recoit son bouton a la publication (le go a lieu
apres la sortie : l'episode est deja dans le flux).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ecoute  # noqa: E402
from enrich_episodes import _lire, _texte, _secondes  # noqa: E402

ROOT = Path(__file__).parent.parent
FLUX = "https://feed.ausha.co/Lg58KteQRXlW"     # MediaCritic (lookup Apple id1853247643)
LOGO = "https://www.mediacritic.fr/assets/logo.png"
D1, F1 = "<!-- mc-ecoute -->", "<!-- /mc-ecoute -->"
D2, F2 = "<!-- mc-ecoute-data -->", "<!-- /mc-ecoute-data -->"


def episodes_du_flux():
    x = _lire(FLUX, ko=4000)
    out = {}
    for it in re.findall(r"<item[ >](.*?)</item>", x, re.S):
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        titre = _texte(t.group(1)) if t else ""
        m = re.search(r"\bEp\s?(\d+)", titre, re.I)
        enc = re.search(r"<enclosure\b[^>]*\burl=[\"']([^\"']+)[\"']", it)
        if not (m and enc):
            continue
        du = re.search(r"<itunes:duration>(.*?)</itunes:duration>", it, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", it)
        out[int(m.group(1))] = {"titre": titre, "audio": _texte(enc.group(1)),
                                "duree": _secondes(du.group(1)) if du else None,
                                "date": d.group(1)[5:16] if d else ""}
    return out


def retirer(html, debut, fin):
    return re.sub(re.escape(debut) + r".*?" + re.escape(fin), "", html, flags=re.S)


def main():
    flux = episodes_du_flux()
    if not flux:
        print("  ! flux MediaCritic illisible : pages épisodes inchangées")
        return
    revues = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
    faits = 0
    table = {}          # page -> element : bouton « + » des cartes (assets/liste.js)
    for num, r in revues.items():
        page = ROOT / "episodes" / (r.get("page") or "")
        ep = flux.get(int(num))
        if not page.is_file() or not ep:
            continue
        html = page.read_text(encoding="utf-8")
        avant = html
        html = retirer(retirer(html, D1, F1), D2, F2)
        item = ecoute.element(ep, "MediaCritic", f"/episodes/{page.name}", LOGO)
        item["titre"] = ep["titre"]
        table[page.name] = item
        if 'class="ep-actions-row">' not in html or "</body>" not in html:
            continue
        html = html.replace('class="ep-actions-row">',
                            'class="ep-actions-row">' + D1 + ecoute.boutons(item, libelle=True) + F1, 1)
        html = html.replace("</body>", D2 + ecoute.donnees([item]) + ecoute.SCRIPT + F2 + "\n</body>", 1)
        if html != avant:
            page.write_text(html, encoding="utf-8")
            faits += 1
    sortie = ROOT / "data" / "ecoute-mc.json"
    neuf = json.dumps(table, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if not sortie.exists() or sortie.read_text(encoding="utf-8") != neuf:
        sortie.write_text(neuf, encoding="utf-8")
    print(f"  épisodes : lecteur du site posé ou mis à jour sur {faits} page(s), {len(flux)} épisode(s) dans le flux")


if __name__ == "__main__":
    main()
