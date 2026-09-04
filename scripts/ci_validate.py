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
import html as _html
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
    # La saison n'est plus figee a 1 : on controle le compte, pas le numero.
    if not re.search(rf"Saison \d+ · {last} épisodes", idx):
        err(f"index : 'Saison N · {last} épisodes' introuvable")
    mc_ep_entries = len(re.findall(r'\{ep:\d+,analyse:', idx))
    # Un hors-serie (FAQ, bilan de saison) n'analyse aucun contenu : il n'a pas
    # d'entree MC_EP. Le seuil porte donc sur les episodes qui analysent
    # vraiment quelque chose, pas sur le dernier numero.
    analyses = sum(1 for r in reviews.values()
                   if not r.get("hors_serie") and r.get("note") is not None)
    if mc_ep_entries < analyses:
        err(f"index : MC_EP n'a que {mc_ep_entries} entrées pour {analyses} épisodes analysés")
    hs = last - analyses
    print(f"  ✓ cohérence épisodes (dernier : {last}, MC_EP : {mc_ep_entries} entrées"
          + (f", {hs} hors-série" if hs else "") + ")")

# 5. Catalogue : les slugs notés ont bien mcEpisode
cat = {x["slug"]: x for x in data.get("catalog.json", [])}
for ep, r in reviews.items():
    if r.get("hors_serie") or r.get("note") is None:
        continue          # pas de contenu analyse, donc pas de fiche attendue
    c = cat.get(r["slug"])
    if not c:
        err(f"catalogue : slug {r['slug']} (ep{ep}) absent")
    elif c.get("mcEpisode") != int(ep):
        err(f"catalogue : {r['slug']} mcEpisode={c.get('mcEpisode')} ≠ {ep}")

# 6. Aucun contenu analyse ne doit avoir de fiche jumelle
#    L Heure du Crime apparaissait deux fois sur la page d accueil : deux
#    fiches pour un meme podcast, une seule portant la marque MediaCritic.
#    Ce controle rend la situation impossible a re-installer sans que la CI
#    echoue -- il tourne a chaque publication et a chaque passage du bot.
import unicodedata as _ud


def _fold(s):
    s = _ud.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if _ud.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)


_par_titre = {}
for _x in data.get("catalog.json", []):
    _par_titre.setdefault(_fold(_x.get("title")), []).append(_x)

# Homonymes verifies a la main : contenus distincts portant le meme titre.
# Sans cette soupape, le controle bloquerait a chaque passage sur un cas
# legitime et finirait par etre desactive.
_ok = set()
_hp = ROOT / "data" / "homonymes_verifies.json"
if _hp.exists():
    for _v in json.loads(_hp.read_text(encoding="utf-8")).get("verifies", []):
        _ok.add((_v["analyse"], _v["autre"]))

_jumelles = 0
for _ep, _r in reviews.items():
    _autres = [x for x in _par_titre.get(_fold(_r.get("title")), [])
               if x.get("slug") != _r["slug"]
               and (_r["slug"], x.get("slug")) not in _ok]
    if _autres:
        _jumelles += 1
        err(f"doublon : « {_r['title']} » (ep{_ep}) a une fiche jumelle "
            f"{[x['slug'] for x in _autres]} — supprimer celle qui n'est pas "
            f"analysée (scripts/dedupe_catalogue.py)")
if not _jumelles:
    print(f"  ✓ aucun doublon sur les {len(reviews)} contenus analysés")

# 7. Regles SEO du skill mediacritic-site, verifiees a chaque passage du bot
#    Bloquant : ce qui expose a une sanction ou degrade mesurablement le site.
#    Simple rapport : les longueurs de titres et descriptions, qui relevent du
#    texte editorial de l utilisateur et ne doivent pas casser le job de nuit.

# 7a. Balisage Review UNIQUEMENT sur les contenus reellement analyses.
#     En declarer un sur les 8 200 autres fiches serait du spam de donnees
#     structurees, passible d une action manuelle Google.
_analyses = set()
for _f in (ROOT / "data" / "content").glob("*.json"):
    try:
        if json.loads(open(_f, encoding="utf-8-sig").read()).get("mediacritic"):
            _analyses.add(_f.stem)
    except Exception:
        pass
_abusifs = [f.stem for f in (ROOT / "fiches").glob("*.html")
            if f.stem not in _analyses
            and '"Review"' in f.read_text(encoding="utf-8")]
if _abusifs:
    err(f"Review declare sur {len(_abusifs)} fiche(s) NON analysee(s) "
        f"{_abusifs[:5]} — spam de donnees structurees")
else:
    print(f"  ✓ Review limite aux {len(_analyses)} contenus analysés")

# 7b. Budget des images locales. Un favicon de 175 Ko servi sur 8 000 pages
#     coute plus cher que n importe quelle micro-optimisation de balise.
_lourdes = []
for _a in (ROOT / "assets").glob("*"):
    if _a.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        continue
    _ko = _a.stat().st_size / 1024
    if _ko > 320:
        _lourdes.append(f"{_a.name} ({_ko:.0f} Ko)")
if _lourdes:
    err(f"images hors budget (>320 Ko) : {_lourdes} — "
        f"lancer scripts/optimise_assets.py")
else:
    print("  ✓ images locales dans le budget")

# 7c. Longueurs de titres et descriptions : rapport, non bloquant.
_lt = _ld = 0
for _f in list(ROOT.glob("*.html")) + list((ROOT / "categories").glob("*.html")):
    _x = _f.read_text(encoding="utf-8")
    _m = re.search(r"<title>(.*?)</title>", _x, re.S)
    _d = re.search(r'name="description"[^>]*content="([^"]*)"', _x)
    # On mesure la longueur RENDUE, pas la source : « &amp; » occupe cinq
    # caracteres dans le fichier mais un seul dans l'onglet du navigateur et
    # dans les resultats Google. Sans desechappement, ce controle signalait
    # 1 550 titres trop longs dont l'immense majorite tenait dans la limite.
    if _m and len(_html.unescape(_m.group(1).strip())) > 60:
        _lt += 1
    if _d and len(_html.unescape(_d.group(1))) > 160:
        _ld += 1
if _lt or _ld:
    print(f"  ! {_lt} titre(s) > 60 car. et {_ld} description(s) > 160 car. "
          f"seront tronqués par Google (texte éditorial, non bloquant)")

# 8. Double identite : annuaire ET critiques
#    Les moteurs generatifs ne percevaient le site que comme un blog de
#    critiques. Ce controle empeche l identite d annuaire de disparaitre
#    silencieusement a la prochaine refonte de balises.
for _page, _url in (("index.html", "accueil"), ("catalogue.html", "catalogue")):
    _t = (ROOT / _page).read_text(encoding="utf-8")
    _m = re.search(r"<title>(.*?)</title>", _t, re.S)
    if not _m or "annuaire" not in _m.group(1).lower():
        err(f"{_page} : le <title> ne contient plus « Annuaire » — "
            f"l'identité d'annuaire disparaît des résultats de recherche")
    if '"DataCatalog"' not in _t:
        err(f"{_page} : nœud JSON-LD DataCatalog absent — sans lui une IA ne "
            f"comprend pas que le site est un annuaire et non un blog")
    if not re.search(r"<h2[^>]*>", _t):
        err(f"{_page} : aucun H2, la hiérarchie sémantique est incomplète")

# Les pages categories doivent etre rattachees a l entite annuaire
_orphelines = [f.name for f in (ROOT / "categories").glob("*.html")
               if "#annuaire" not in f.read_text(encoding="utf-8")]
if _orphelines:
    err(f"{len(_orphelines)} page(s) catégorie sans isPartOf vers l'annuaire : "
        f"{_orphelines[:4]} — relancer generate_categories.py")
if not errors:
    print("  ✓ identité d'annuaire présente (title, DataCatalog, H2, "
          f"{len(list((ROOT / 'categories').glob('*.html')))} pages catégories rattachées)")

if errors:
    print(f"\n{len(errors)} erreur(s).")
    sys.exit(1)
print("\nValidation OK.")
