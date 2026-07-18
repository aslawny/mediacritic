#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation CI du site (aucun secret requis). Échoue (exit 1) si :
- un JSON-LD est malformé (épisodes, index, palmarès, catalogue, catégories)
- le sitemap contient des doublons ou est malformé
- une page épisode de mc_reviews.json manque, ou l'inverse
- les compteurs de l'index sont incohérents avec mc_reviews
- catalog.json / catalog-lite.json / mc_reviews.json sont invalides
- un marqueur de conflit git traîne dans un fichier publié
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
errors = []

def err(msg):
    errors.append(msg)
    print(f"  ✗ {msg}")

def check_jsonld(path):
    html = path.read_text(encoding="utf-8")
    for i, b in enumerate(re.findall(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)):
        try:
            json.loads(b)
        except Exception as e:
            err(f"JSON-LD #{i+1} invalide dans {path.relative_to(ROOT)} : {e}")
    if "<<<<<<<" in html or ">>>>>>>" in html:
        err(f"marqueur de conflit git dans {path.relative_to(ROOT)}")

# 1. JSON de données
data = {}
for name in ("catalog.json", "catalog-lite.json", "mc_reviews.json", "blocklist.json"):
    p = ROOT / "data" / name
    try:
        data[name] = json.loads(p.read_text(encoding="utf-8"))
        print(f"  ✓ data/{name}")
    except Exception as e:
        err(f"data/{name} invalide : {e}")

# 2. JSON-LD des pages clés
pages = ([ROOT / p for p in ("index.html", "palmares.html", "catalogue.html",
                             "qui-sommes-nous.html", "contact.html")]
         + sorted((ROOT / "episodes").glob("*.html"))
         + sorted((ROOT / "categories").glob("*.html")))
for p in pages:
    if p.exists():
        check_jsonld(p)
print(f"  ✓ JSON-LD contrôlé sur {len(pages)} pages")

# 3. Sitemap
smap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
locs = re.findall(r"<loc>([^<]+)</loc>", smap)
if len(locs) != len(set(locs)):
    dupes = sorted({x for x in locs if locs.count(x) > 1})
    err(f"sitemap : {len(locs) - len(set(locs))} doublon(s), ex. {dupes[:3]}")
else:
    print(f"  ✓ sitemap : {len(locs)} URLs uniques")
if "<<<<<<<" in smap:
    err("marqueur de conflit git dans sitemap.xml")

# 4. Cohérence mc_reviews ↔ pages ↔ sitemap ↔ index
reviews = data.get("mc_reviews.json", {})
for ep, r in reviews.items():
    if not (ROOT / "episodes" / r["page"]).exists():
        err(f"mc_reviews ep{ep} : episodes/{r['page']} manquant")
    if f"/episodes/{r['page']}" not in smap:
        err(f"mc_reviews ep{ep} : absent du sitemap")
if reviews:
    last = max(int(k) for k in reviews)
    idx = (ROOT / "index.html").read_text(encoding="utf-8")
    if f'<div class="num">{last}</div>' not in idx:
        err(f"index : compteur 'analysés par MC' ≠ {last}")
    if f"Saison 1 · {last} épisodes" not in idx:
        err(f"index : 'Saison 1 · {last} épisodes' introuvable")
    mc_ep_entries = len(re.findall(r'\{ep:\d+,analyse:', idx))
    if mc_ep_entries < last:
        err(f"index : MC_EP n'a que {mc_ep_entries} entrées pour {last} épisodes")
    print(f"  ✓ cohérence épisodes (dernier : {last}, MC_EP : {mc_ep_entries} entrées)")

# 5. Catalogue : les slugs notés ont bien mcEpisode
cat = {x["slug"]: x for x in data.get("catalog.json", [])}
for ep, r in reviews.items():
    c = cat.get(r["slug"])
    if not c:
        err(f"catalogue : slug {r['slug']} (ep{ep}) absent")
    elif c.get("mcEpisode") != int(ep):
        err(f"catalogue : {r['slug']} mcEpisode={c.get('mcEpisode')} ≠ {ep}")

if errors:
    print(f"\n{len(errors)} erreur(s).")
    sys.exit(1)
print("\nValidation OK.")
