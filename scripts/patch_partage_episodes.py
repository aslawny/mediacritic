#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ajoute la rangee de partage aux pages episodes.

Les fiches savent se partager depuis generate_fiches.py, mais les pages
episodes -- la ou se trouve reellement la critique -- n'avaient rien. C'est
pourtant ce qu'on partage : « Floodcast : 8,5/10 » renvoie vers l'analyse,
pas vers une entree d'annuaire.

Aucun widget tiers : quatre liens <a> et un bouton de copie. Zero requete
reseau, zero cookie, et compatible avec la CSP du site.

Idempotent : une page deja traitee n'est pas retouchee. Sans argument, le
script traite toutes les pages de episodes/ -- c'est ce qui permet de
l'appeler apres chaque publication sans rien lui passer.

Usage : python scripts/patch_partage_episodes.py [fichiers...]
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
REVIEWS = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
PAR_PAGE = {r["page"]: r for r in REVIEWS.values()}

RESEAUX = (
    ("X", "https://twitter.com/intent/tweet?text={texte}&url={url}", "x"),
    ("LinkedIn", "https://www.linkedin.com/sharing/share-offsite/?url={url}", "li"),
    ("Facebook", "https://www.facebook.com/sharer/sharer.php?u={url}", "fb"),
    ("WhatsApp", "https://wa.me/?text={texte}%20{url}", "wa"),
)

CSS = """<style>/* mc-partage */
.pt-card h2{margin-bottom:12px}
.pt-row{display:flex;gap:8px;flex-wrap:wrap}
.pt-btn{display:inline-block;padding:8px 15px;border-radius:9px;border:1px solid rgba(255,255,255,.10);font-size:.85rem;font-weight:600;text-decoration:none;cursor:pointer;font-family:inherit;line-height:1.4;transition:border-color .15s}
.pt-btn:hover{border-color:var(--c-orange)}
.pt-x,.pt-copie{background:rgba(255,255,255,.05);color:#e8eaed}
.pt-li{background:rgba(10,102,194,.14);color:#6aa9e0}
.pt-fb{background:rgba(24,119,242,.12);color:#7ab0f5}
.pt-wa{background:rgba(37,211,102,.12);color:#5fd68f}
@media(max-width:520px){.pt-btn{padding:8px 12px;font-size:.8rem}}
</style>"""


def texte_partage(page):
    """Le texte pre-rempli porte la note quand elle existe : « Floodcast :
    8,5/10 sur MediaCritic » se partage, un titre nu non. Un hors-serie n'a
    pas de note -- on ne lui en invente pas."""
    r = PAR_PAGE.get(page)
    if not r:
        return None
    titre = r.get("title") or page
    note = r.get("note")
    if note is not None:
        return "%s : %s/10 — la critique MediaCritic" % (titre, str(note).replace(".", ","))
    return "%s — MediaCritic" % titre


def bloc(page):
    txt = texte_partage(page)
    if txt is None:
        return None
    url = quote("%s/episodes/%s" % (BASE, page), safe="")
    t = quote(txt, safe="")
    liens = "".join(
        '<a class="pt-btn pt-%s" href="%s" target="_blank" '
        'rel="noopener noreferrer nofollow" aria-label="Partager sur %s">%s</a>'
        % (cls, g.format(texte=t, url=url), nom, nom)
        for nom, g, cls in RESEAUX)
    copie = ('<button type="button" class="pt-btn pt-copie" '
             "onclick=\"navigator.clipboard.writeText(location.href).then("
             "()=&gt;{this.textContent='Lien copié';"
             "setTimeout(()=&gt;{this.textContent='Copier le lien'},2000)}"
             ",()=&gt;{this.textContent='Copie impossible'})\">"
             "Copier le lien</button>")
    return ('  <div class="card pt-card">\n    <h2>🔗 Partager cet épisode</h2>\n'
            '    <div class="pt-row">' + liens + copie + "</div>\n  </div>")


def patch(txt, page):
    if "pt-card" in txt:
        return txt, False
    b = bloc(page)
    if b is None:
        return txt, None
    if "</head>" not in txt:
        return txt, None
    txt = txt.replace("</head>", CSS + "\n</head>", 1)
    # Juste avant la navigation precedent/suivant : on a lu la critique, on
    # partage, puis on passe a l'episode suivant.
    m = re.search(r'\n\s*<nav class="nav-ep"|\n\s*<nav[^>]*>\s*<a[^>]*nav-ep-btn', txt)
    if m:
        return txt[:m.start()] + "\n" + b + txt[m.start():], True
    if "\n<footer>" in txt:
        return txt.replace("\n<footer>", "\n" + b + "\n</div>\n\n<footer>", 1), True
    return txt, None


def main():
    cibles = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "episodes").glob("*.html"))
    faits = deja = rates = 0
    for f in cibles:
        out, etat = patch(f.read_text(encoding="utf-8"), f.name)
        if etat is None:
            rates += 1
            print("  ! non traité : %s" % f.name)
        elif etat:
            f.write_text(out, encoding="utf-8")
            faits += 1
        else:
            deja += 1
    print("%d page(s) mise(s) à jour, %d déjà à jour, %d ignorée(s)" % (faits, deja, rates))


if __name__ == "__main__":
    main()
