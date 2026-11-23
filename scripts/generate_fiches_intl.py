#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fiches du catalogue international (23/11/2026) : data/content_intl/*.json
-> fiches/{slug}.html (meme gabarit que les fiches francaises, via
generate_fiches.render_fiche) + data/catalog-intl.json + sitemap.

Isole du catalogue francais : index des « similaires » propre (un podcast
americain recommande d'autres contenus internationaux de sa langue, jamais
une fiche francaise, et inversement), catalogue a part (charge par l'accueil
et l'annuaire seulement quand on choisit une autre langue), pas de label
« independant » (nos listes d'editeurs sont francaises : le tri se
tromperait).

Le sitemap n'est jamais purge ici : generate_fiches s'en charge (il ne retire
que les URL dont le fichier n'existe plus).

Usage : python scripts/generate_fiches_intl.py
"""
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
import generate_fiches as gf  # noqa: E402

ROOT = Path(__file__).parent.parent
INTL = ROOT / "data" / "content_intl"
CATALOG = ROOT / "data" / "catalog-intl.json"
LANGUES = {"en": "English", "es": "Español", "de": "Deutsch", "it": "Italiano", "pt": "Português"}


def rendre(groupe, slugs_modifies):
    faits = modifies = 0
    for p, d in groupe:
        fiche = gf.FICHES_DIR / f"{d['slug']}.html"
        if not gf.needs_update(p, fiche):
            continue
        html = gf.render_fiche(d)
        # La page « Desirs & intimite » est francophone : la section sensuelle
        # d'une autre langue est l'annuaire filtre sur cette langue.
        html = html.replace("../categories/podcasts-erotiques.html",
                            f"../catalogue.html?langue={d['langue']}&amp;cat=desirs")
        ancien = fiche.read_text(encoding="utf-8") if fiche.exists() else None
        if ancien == html:
            continue
        fiche.write_text(html, encoding="utf-8")
        faits += 1
        if ancien is None or " ".join(ancien.split()) != " ".join(html.split()):
            slugs_modifies.add(d["slug"])
            modifies += 1
    return faits, modifies


def main():
    fichiers = sorted(INTL.glob("*.json")) if INTL.exists() else []
    donnees = []
    for p in fichiers:
        try:
            d = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as e:
            print(f"  ! {p.name} : {e}")
            continue
        if d.get("slug") and d.get("langue") in LANGUES:
            donnees.append((p, d))
    gf.est_independant = lambda d: False          # pas de label hors francophonie
    # Section sensuelle : champ `desirs` pose a l'import (desirs_intl), pas les
    # mots-cles francais de desirs.py.
    gf.desirs_section = lambda d: d.get("desirs")
    gf.DESC_PARTAGEES.clear()
    faits = modifies = 0
    slugs_modifies = set()
    # Langue par langue : « À découvrir aussi » reste dans la langue de la
    # fiche, et les liens de categorie menent a l'annuaire filtre sur cette
    # langue (les pages categories/ sont francophones).
    for lg in LANGUES:
        groupe = [(p, d) for p, d in donnees if d["langue"] == lg]
        if not groupe:
            continue
        gf.construire_index([d for _, d in groupe])
        gf.category_href = (lambda l: lambda cat: f"../catalogue.html?langue={l}&amp;cat={quote(cat)}")(lg)
        f, m = rendre(groupe, slugs_modifies)
        faits += f
        modifies += m
    catalogue = []
    for _, d in sorted(donnees, key=lambda x: x[1]["slug"]):
        ap = (d.get("platforms") or {}).get("apple") or {}
        catalogue.append({
            "slug": d["slug"], "title": d.get("title"), "author": d.get("author", ""),
            "type": d.get("type"), "categories": d.get("categories", []), "image": d.get("image"),
            "description": (d.get("description") or "")[:80], "hasMediacritic": False,
            "rating": ap.get("rating"), "ratingCount": ap.get("ratingCount"),
            "subscribers": ((d.get("platforms") or {}).get("youtube") or {}).get("subscribers"),
            "addedAt": d.get("updatedAt", ""), "langue": d["langue"], "pays": d.get("pays", ""),
        })
        if d.get("desirs"):
            catalogue[-1]["desirs"] = d["desirs"]
    neuf = json.dumps(catalogue, ensure_ascii=False, separators=(",", ":"))
    if not CATALOG.exists() or CATALOG.read_text(encoding="utf-8") != neuf:
        CATALOG.write_text(neuf, encoding="utf-8")
    gf.update_sitemap([d["slug"] for _, d in donnees], slugs_modifies)
    par_langue = {}
    for _, d in donnees:
        par_langue[d["langue"]] = par_langue.get(d["langue"], 0) + 1
    print(f"  international : {len(donnees)} fiches {par_langue}, {faits} écrite(s), "
          f"catalog-intl.json → {len(catalogue)} entrées")


if __name__ == "__main__":
    main()
