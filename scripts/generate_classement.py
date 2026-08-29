#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genere classement.html : les classements MediaCritic.

Quatre classements, chacun repondant a une question differente. Aucun n'est
fabrique : tous reposent sur des donnees reellement presentes.

  1. Les mieux notes      note Apple, moyenne bayesienne, PLANCHER 500 avis
  2. Les plus populaires  volume d'avis Apple
  3. Top chaines YouTube  abonnes
  4. Les pepites          notes MediaCritic

Pourquoi un plancher de 500 avis sur le classement qualite : un tri par
moyenne brute placait en tete des podcasts a 5,0 sur 300 avis -- HelloSolos,
Investir avec Xavier -- pendant que Les Grosses Tetes et Affaires sensibles
disparaissaient. Un classement que personne en France ne trouverait credible,
donc contre-productif. La moyenne bayesienne seule ne corrigeait pas assez :
il fallait un seuil de notoriete. Avec 500 avis, 351 podcasts restent
eligibles et le haut du classement devient defendable.

« Les contenus qui montent » n'apparait PAS ici : l'historique commence le
24/08/2026, il faudra 4 a 6 semaines. Voir scripts/snapshot_metrics.py.

Usage : python scripts/generate_classement.py
"""
import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"
PLANCHER_AVIS = 500
M_BAYES = 500


def h(s):
    return html.escape(str(s or ""), quote=True)


def _css():
    """CSS repris d'une page categorie : meme identite visuelle, zero
    duplication de maintenance."""
    src = subprocess.run(["git", "show", "HEAD:categories/gaming.html"],
                         cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8").stdout
    m = re.search(r"<style>.*?</style>", src, re.DOTALL)
    return m.group(0) if m else "<style></style>"


def _nombre(n):
    return f"{int(n):,}".replace(",", " ")


def ligne(rang, item, valeur, legende):
    slug = item.get("slug")
    img = item.get("image")
    if img:
        vign = f'<img src="{h(img)}" alt="{h(item.get("title"))}" loading="lazy" />'
    else:
        ini = "".join(w[0].upper() for w in (item.get("title") or "?").split()[:2])
        vign = f'<span class="cl-ph">{h(ini)}</span>'
    badge = ""
    if item.get("mcNote"):
        note = str(item["mcNote"]).replace(".", ",")
        badge = f'<span class="cl-mc">★ {h(note)}/10</span>'
    return (
        f'<li class="cl-item"><span class="cl-rang">{rang}</span>'
        f'<a class="cl-lien" href="fiches/{h(slug)}.html">'
        f'<span class="cl-cover">{vign}</span>'
        f'<span class="cl-txt"><span class="cl-titre">{h(item.get("title"))}</span>'
        f'<span class="cl-auteur">{h((item.get("author") or "")[:40])}</span></span></a>'
        f'<span class="cl-val">{valeur}<span class="cl-leg">{legende}</span></span></li>')


def section(cle, titre, chapo, items, valeur, legende):
    if not items:
        return "", None
    lignes = "".join(ligne(i + 1, x, valeur(x), legende) for i, x in enumerate(items))
    bloc = (f'<section class="cl-section" id="{cle}">'
            f'<h2>{h(titre)}</h2><p class="cl-chapo">{h(chapo)}</p>'
            f'<ol class="cl-list">{lignes}</ol></section>')
    ld = {"@type": "ItemList", "name": titre, "numberOfItems": len(items),
          "itemListElement": [
              {"@type": "ListItem", "position": i + 1,
               "url": f'{BASE}/fiches/{x["slug"]}.html', "name": x.get("title")}
              for i, x in enumerate(items[:30])]}
    return bloc, ld


def main():
    cat = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    pods = [x for x in cat if x.get("type") != "youtube"
            and x.get("rating") and x.get("ratingCount")]
    moyenne = sum(float(x["rating"]) for x in pods) / max(1, len(pods))

    def bayes(x):
        v = int(x["ratingCount"])
        return (v / (v + M_BAYES)) * float(x["rating"]) + (M_BAYES / (v + M_BAYES)) * moyenne

    eligibles = [x for x in pods if int(x["ratingCount"]) >= PLANCHER_AVIS]
    mieux_notes = sorted(eligibles, key=lambda x: -bayes(x))[:50]
    populaires = sorted(pods, key=lambda x: -int(x["ratingCount"]))[:50]
    chaines = sorted([x for x in cat if x.get("type") == "youtube" and x.get("subscribers")],
                     key=lambda x: -int(x["subscribers"]))[:30]
    pepites = sorted([x for x in cat if x.get("mcNote")],
                     key=lambda x: (-float(x["mcNote"]), x.get("title", "").lower()))

    sections, listes = [], []
    for args in (
        ("mieux-notes", "Les podcasts les mieux notés",
         f"Note Apple Podcasts, parmi les {len(eligibles)} podcasts comptant au moins "
         f"{PLANCHER_AVIS} avis. En dessous de ce seuil, une moyenne parfaite ne veut "
         f"rien dire.", mieux_notes,
         lambda x: f'{float(x["rating"]):.1f}'.replace(".", ","), "sur 5"),
        ("populaires", "Les podcasts les plus populaires",
         "Classés par nombre d'avis déposés sur Apple Podcasts — la mesure la plus "
         "objective de l'audience d'un podcast.", populaires,
         lambda x: _nombre(x["ratingCount"]), "avis"),
        ("chaines", "Les chaînes YouTube francophones les plus suivies",
         "Classées par nombre d'abonnés.", chaines,
         lambda x: _nombre(x["subscribers"]), "abonnés"),
        ("pepites", "Les pépites MediaCritic",
         "Les contenus que nous avons écoutés, analysés et notés en détail dans le "
         "podcast. Notre avis, pas celui d'un algorithme.", pepites,
         lambda x: str(x["mcNote"]).replace(".", ","), "sur 10"),
    ):
        bloc, ld = section(*args)
        if bloc:
            sections.append(bloc)
            listes.append(ld)

    total = (len(cat) // 100) * 100
    # 49 caracteres : au-dela de 60, Google tronque.
    titre = "Classement des podcasts francophones | MediaCritic"
    desc = (f"Le classement des meilleurs podcasts et chaînes YouTube francophones : "
            f"les mieux notés, les plus populaires, et les pépites MediaCritic.")

    ld = {"@context": "https://schema.org", "@graph": listes + [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Classement",
             "item": f"{BASE}/classement.html"}]},
        {"@type": "DataCatalog", "@id": BASE + "/#annuaire",
         "name": "Annuaire MediaCritic des podcasts et chaînes YouTube francophones",
         "url": f"{BASE}/catalogue.html", "inLanguage": "fr-FR",
         "isAccessibleForFree": True},
    ]}

    nav = ('<nav><div class="nav-left">'
           f'<a href="index.html" class="nav-back">← Accueil</a>'
           '<span class="nav-brand">MediaCritic</span></div>'
           '<div class="nav-links">'
           '<a href="catalogue.html">Annuaire</a>'
           '<a href="classement.html" class="active">Classement</a>'
           '<a href="palmares.html">🏆 Palmarès</a></div></nav>')

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(titre)}</title>
<meta name="description" content="{h(desc)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{BASE}/classement.html" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE}/classement.html" />
<meta property="og:title" content="{h(titre)}" />
<meta property="og:description" content="{h(desc)}" />
<meta property="og:image" content="{BASE}/assets/banner.png" />
<meta property="og:locale" content="fr_FR" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Classement des podcasts francophones — MediaCritic" />
<meta name="twitter:description" content="{h(desc)}" />
<meta name="twitter:image" content="{BASE}/assets/banner.png" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{_css()}
<style>
.cl-section{{max-width:820px;margin:0 auto 52px;padding:0 clamp(16px,4vw,32px)}}
.cl-section h2{{font-family:'Syne',sans-serif;font-size:1.35rem;font-weight:800;margin-bottom:6px}}
.cl-chapo{{color:var(--c-muted);font-size:.9rem;line-height:1.6;margin-bottom:20px}}
.cl-list{{list-style:none;display:flex;flex-direction:column;gap:2px}}
.cl-item{{display:flex;align-items:center;gap:12px;padding:9px 10px;border-radius:10px;transition:background .18s}}
.cl-item:hover{{background:rgba(255,255,255,.04)}}
.cl-rang{{flex:0 0 30px;text-align:right;font-family:'Syne',sans-serif;font-weight:800;color:var(--c-muted2);font-size:.95rem}}
.cl-lien{{flex:1;display:flex;align-items:center;gap:12px;min-width:0}}
.cl-cover{{flex:0 0 44px;height:44px;border-radius:8px;overflow:hidden;background:linear-gradient(135deg,#1a2030,#0d1220);display:flex;align-items:center;justify-content:center}}
.cl-cover img{{width:100%;height:100%;object-fit:cover;display:block}}
.cl-ph{{font-family:'Syne',sans-serif;font-weight:800;color:rgba(255,255,255,.5);font-size:.85rem}}
.cl-txt{{min-width:0;display:flex;flex-direction:column}}
.cl-titre{{font-weight:600;font-size:.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cl-item:hover .cl-titre{{color:var(--c-orange)}}
.cl-auteur{{font-size:.75rem;color:var(--c-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cl-val{{flex:0 0 auto;text-align:right;font-weight:700;font-size:.95rem;display:flex;flex-direction:column;line-height:1.2}}
.cl-leg{{font-size:.66rem;font-weight:500;color:var(--c-muted);text-transform:uppercase;letter-spacing:.05em}}
.cl-mc{{display:none}}
.cl-intro{{max-width:820px;margin:0 auto 40px;padding:0 clamp(16px,4vw,32px)}}
.cl-somm{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}}
.cl-somm a{{font-size:.8rem;font-weight:600;padding:6px 14px;border-radius:99px;background:var(--c-glass);border:1px solid var(--c-border);color:var(--c-muted2)}}
.cl-somm a:hover{{border-color:rgba(232,98,45,.4);color:var(--c-text)}}
@media(max-width:520px){{.cl-cover{{flex:0 0 36px;height:36px}}.cl-rang{{flex:0 0 22px;font-size:.85rem}}}}
</style>
</head>
<body>
{nav}
<header class="cl-intro">
  <h1 style="font-family:'Syne',sans-serif;font-size:clamp(1.6rem,4.5vw,2.4rem);font-weight:800;line-height:1.15;margin-bottom:12px">
    Le classement des podcasts et chaînes YouTube francophones</h1>
  <p style="color:var(--c-muted);line-height:1.7">
    Quatre classements tirés de notre annuaire de {_nombre(total)}+ contenus. Les notes
    et les audiences viennent des plateformes ; les pépites, de nos propres critiques.
    Mis à jour automatiquement.</p>
  <div class="cl-somm">
    <a href="#mieux-notes">Les mieux notés</a>
    <a href="#populaires">Les plus populaires</a>
    <a href="#chaines">Top YouTube</a>
    <a href="#pepites">Pépites MediaCritic</a>
  </div>
</header>
{"".join(sections)}
<footer style="text-align:center;padding:30px;border-top:1px solid var(--c-border);color:var(--c-muted);font-size:.8rem">
  <p>© {date.today().year} <a href="index.html" style="color:var(--c-muted)">MediaCritic</a> —
  <a href="catalogue.html" style="color:var(--c-muted)">Annuaire</a> —
  <a href="palmares.html" style="color:var(--c-muted)">Palmarès</a></p>
</footer>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>
</body>
</html>"""

    (ROOT / "classement.html").write_text(page, encoding="utf-8")
    print(f"classement.html généré — {len(mieux_notes)} mieux notés, "
          f"{len(populaires)} populaires, {len(chaines)} chaînes, {len(pepites)} pépites")
    print(f"  plancher qualité : {PLANCHER_AVIS} avis ({len(eligibles)} éligibles)")


if __name__ == "__main__":
    main()
