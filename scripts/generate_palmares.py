#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère palmares.html : le classement officiel des podcasts et chaînes notés
par MediaCritic, à partir de data/mc_reviews.json (notes) et data/catalog.json
(images, catégories, types). Podium top 3, classement complet, filtres par
grande famille, JSON-LD ItemList.

Usage : python scripts/generate_palmares.py
"""
import json, re, html, subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"

REVIEWS = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
CATALOG = {x["slug"]: x for x in json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))}

# CSS partagé, repris de la page catégorie modèle (déterministe via git)
_model = subprocess.run(["git", "show", "HEAD:categories/gaming.html"],
                        cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
CSS = re.search(r"<style>.*?</style>", _model, re.DOTALL).group(0)

EXTRA_CSS = """<style>
.podium{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;max-width:900px;margin:8px auto 34px;padding:0 clamp(16px,4vw,48px)}
@media(max-width:640px){.podium{grid-template-columns:1fr}}
.podium-card{background:var(--c-card);border:1px solid rgba(232,98,45,.35);border-radius:16px;padding:22px;text-align:center;position:relative}
.podium-card.first{border-color:#f5a623;box-shadow:0 8px 32px rgba(245,166,35,.15)}
.podium-rank{font-size:1.6rem;margin-bottom:6px}
.podium-card img{width:88px;height:88px;border-radius:14px;object-fit:cover;margin:0 auto 12px}
.podium-note{font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;background:linear-gradient(90deg,#e8622d,#f5a623);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.podium-title{font-weight:700;font-size:.95rem;margin:6px 0 4px}
.podium-verdict{font-size:.76rem;color:var(--c-muted);line-height:1.5}
.rank-list{max-width:900px;margin:0 auto;padding:0 clamp(16px,4vw,48px);display:flex;flex-direction:column;gap:10px}
.rank-row{display:flex;align-items:center;gap:16px;background:var(--c-card);border:1px solid var(--c-border);border-radius:12px;padding:12px 18px;transition:border-color .2s}
.rank-row:hover{border-color:rgba(232,98,45,.4)}
.rank-pos{font-family:'Syne',sans-serif;font-weight:800;font-size:1.05rem;color:var(--c-muted);width:34px;flex-shrink:0;text-align:center}
.rank-row img{width:52px;height:52px;border-radius:10px;object-fit:cover;flex-shrink:0}
.rank-cover-ph{width:52px;height:52px;border-radius:10px;background:var(--c-bg3);display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1.3rem}
.rank-main{flex:1;min-width:0}
.rank-title{font-weight:700;font-size:.92rem}
.rank-verdict{font-size:.76rem;color:var(--c-muted);line-height:1.45;margin-top:2px}
.rank-meta{font-size:.7rem;color:var(--c-muted2);margin-top:3px}
.rank-note{font-family:'Syne',sans-serif;font-weight:800;font-size:1.25rem;background:linear-gradient(90deg,#e8622d,#f5a623);-webkit-background-clip:text;-webkit-text-fill-color:transparent;white-space:nowrap;flex-shrink:0}
.rank-ep{font-size:.68rem;color:var(--c-muted2);white-space:nowrap;flex-shrink:0}
.pal-filters{display:flex;gap:8px;flex-wrap:wrap;max-width:900px;margin:0 auto 22px;padding:0 clamp(16px,4vw,48px)}
.pal-btn{font-size:.78rem;font-weight:600;padding:6px 14px;border-radius:20px;background:var(--c-glass);border:1px solid var(--c-border2);color:var(--c-muted);cursor:pointer;transition:all .2s}
.pal-btn:hover,.pal-btn.active{color:#fff;background:var(--c-orange);border-color:var(--c-orange)}
@media(max-width:600px){.rank-verdict{display:none}}
</style>"""

FAMILIES = [
    ("tous", "Tous", None),
    ("culture", "Culture & Histoire", {"histoire", "culture", "recit", "radio", "enfants", "education", "bd", "litterature", "series"}),
    ("gaming", "Gaming & Geek", {"gaming", "retro", "nostalgie", "culture geek", "jeux inde", "critique", "anime", "manga"}),
    ("sport", "Sport", {"sport", "football", "basket", "nba", "running", "endurance", "fitness"}),
    ("humour", "Humour & Société", {"humour", "comedie", "societe", "vlogs", "true crime", "interview"}),
    ("savoir", "Sciences & Tech", {"sciences", "vulgarisation", "tech", "numerique", "dev", "economie", "business", "psychologie", "emotions"}),
    ("gastronomie", "Gastronomie & Vie", {"gastronomie", "cuisine", "DIY", "maison", "renovation", "bien-etre", "dessin", "creation"}),
]

def h(s):
    return html.escape(str(s), quote=True)

def fmt_note(n):
    return str(n).replace(".", ",").replace(",0", "")

def family_of(cats):
    cs = set(cats or [])
    for key, _, members in FAMILIES[1:]:
        if members & cs:
            return key
    return "culture"

def build():
    rows = []
    for ep, r in REVIEWS.items():
        c = CATALOG.get(r["slug"], {})
        rows.append({
            "ep": int(ep), "slug": r["slug"], "title": r["title"],
            "note": r["note"], "verdict": r["verdict"],
            "image": c.get("image"),
            "type": c.get("type", "podcast"),
            "cats": c.get("categories", []),
            "page": r["page"],
        })
    rows.sort(key=lambda x: (-x["note"], x["ep"]))

    today = date.today()
    months = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
    updated = f"{months[today.month-1]} {today.year}"

    title = f"Palmarès MediaCritic — Les meilleurs podcasts et chaînes YouTube francophones notés ({today.year})"
    desc = (f"Le classement officiel MediaCritic : {len(rows)} podcasts et chaînes YouTube francophones "
            f"écoutés, analysés et notés sur 10. En tête : "
            + ", ".join(f'{r["title"]} ({fmt_note(r["note"])}/10)' for r in rows[:3]) + ".")

    # Podium
    medals = ["🥇", "🥈", "🥉"]
    podium = ""
    for i, r in enumerate(rows[:3]):
        img = (f'<img src="{h(r["image"])}" alt="{h(r["title"])}" loading="lazy">' if r["image"]
               else '<div class="rank-cover-ph" style="margin:0 auto 12px;width:88px;height:88px;font-size:2rem;">🎙️</div>')
        cls = "podium-card first" if i == 0 else "podium-card"
        podium += (f'<a class="{cls}" href="episodes/{h(r["page"])}">'
                   f'<div class="podium-rank">{medals[i]}</div>{img}'
                   f'<div class="podium-note">{fmt_note(r["note"])}<span style="font-size:.9rem;">/10</span></div>'
                   f'<div class="podium-title">{h(r["title"])}</div>'
                   f'<div class="podium-verdict">{h(r["verdict"])}</div></a>')

    # Classement complet
    rank_rows = ""
    for i, r in enumerate(rows, 1):
        img = (f'<img src="{h(r["image"])}" alt="{h(r["title"])}" loading="lazy">' if r["image"]
               else f'<div class="rank-cover-ph">{"📺" if r["type"]=="youtube" else "🎙️"}</div>')
        fam = family_of(r["cats"])
        cat0 = h((r["cats"] or [""])[0])
        rank_rows += (f'<a class="rank-row" data-fam="{fam}" href="episodes/{h(r["page"])}">'
                      f'<div class="rank-pos">{i}</div>{img}'
                      f'<div class="rank-main"><div class="rank-title">{h(r["title"])}</div>'
                      f'<div class="rank-verdict">{h(r["verdict"])}</div>'
                      f'<div class="rank-meta">{cat0} · analysé dans l\'épisode {r["ep"]}</div></div>'
                      f'<div class="rank-note">{fmt_note(r["note"])}<span style="font-size:.8rem;">/10</span></div></a>')

    filters = "".join(
        f'<button class="pal-btn{" active" if key == "tous" else ""}" data-fam="{key}">{label}</button>'
        for key, label, _ in FAMILIES)

    # JSON-LD ItemList + Breadcrumb
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "ItemList", "name": "Palmarès MediaCritic des podcasts et chaînes YouTube francophones",
         "numberOfItems": len(rows), "itemListOrder": "https://schema.org/ItemListOrderDescending",
         "itemListElement": [
             {"@type": "ListItem", "position": i,
              "item": {"@type": "PodcastSeries", "name": r["title"],
                       "url": f'{BASE}/fiches/{r["slug"]}.html'}}
             for i, r in enumerate(rows, 1)]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Palmarès", "item": BASE + "/palmares.html"}]},
    ]}

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(title)}</title>
<meta name="description" content="{h(desc)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{BASE}/palmares.html" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE}/palmares.html" />
<meta property="og:title" content="{h(title)}" />
<meta property="og:description" content="{h(desc)}" />
<meta property="og:image" content="{BASE}/assets/banner.png" />
<meta property="og:locale" content="fr_FR" />
<meta property="og:site_name" content="MediaCritic" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@MediaCriticInc" />
<meta name="twitter:title" content="{h(title)}" />
<meta name="twitter:description" content="{h(desc)}" />
<meta name="twitter:image" content="{BASE}/assets/banner.png" />
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<link rel="icon" href="assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
{CSS}
{EXTRA_CSS}
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{GA}");</script>
</head>
<body>
<nav>
<a href="./" class="nav-logo"><img src="assets/logo.png" alt="MediaCritic" /><span>MediaCritic</span></a>
<div class="nav-links">
<a href="./">Catalogue</a>
<a href="palmares.html" style="color:var(--c-orange);">Palmarès</a>
<a href="qui-sommes-nous.html">Qui sommes-nous</a>
<a href="contact.html">Contact</a>
</div>
<a href="https://open.spotify.com/show/5JuffYLQq1q6l7Vh2zvkrV" target="_blank" rel="noopener noreferrer" class="nav-cta">🎧 Écouter</a>
</nav>
<header class="page-header" style="text-align:center;max-width:760px;">
<div class="breadcrumb"><a href="./">MediaCritic</a> · <strong>Palmarès</strong></div>
<h1>🏆 Le Palmarès MediaCritic</h1>
<p class="lede" style="margin:0 auto;">{len(rows)} podcasts et chaînes YouTube francophones écoutés, décortiqués et <strong>notés sur 10</strong> par Alex, Lolo et leurs invité·e·s. Pas d'algorithme, pas de sponsor — juste des oreilles exigeantes et des avis assumés. Mis à jour {updated}.</p>
</header>
<div class="podium">{podium}</div>
<div class="pal-filters">{filters}</div>
<div class="rank-list" id="rank-list">{rank_rows}</div>
<section class="cta-block" style="max-width:760px;margin:44px auto;padding:24px 28px;background:linear-gradient(135deg,rgba(232,98,45,.08),rgba(232,98,45,.02));border:1px solid rgba(232,98,45,.3);border-radius:14px;text-align:center;">
<h3 style="font-family:'Syne',sans-serif;font-size:1.1rem;margin-bottom:8px;">Chaque note a son épisode</h3>
<p style="font-size:.88rem;color:var(--c-muted);margin-bottom:14px;">Derrière chaque note, il y a 5 à 7 minutes d'analyse en audio : fond, forme, intentions. Cliquez sur une ligne pour lire le verdict complet — ou écoutez l'épisode.</p>
<a href="https://open.spotify.com/show/5JuffYLQq1q6l7Vh2zvkrV" target="_blank" rel="noopener noreferrer" style="display:inline-block;padding:10px 22px;background:var(--c-orange);color:#fff;border-radius:8px;font-weight:600;font-size:.88rem;">🎧 Écouter MediaCritic</a>
</section>
<footer>
<div class="footer-inner">
<div class="footer-logo"><img src="assets/logo.png" alt="MediaCritic" /><span>MediaCritic</span></div>
<p class="footer-tagline">Le podcast qui donne son avis, même quand on ne lui a pas demandé.</p>
<div class="footer-links">
<a href="./">Catalogue</a>
<a href="palmares.html">Palmarès</a>
<a href="qui-sommes-nous.html">Qui sommes-nous</a>
<a href="contact.html">Contact</a>
</div>
<p class="footer-copy">© {today.year} MediaCritic — <a href="contact.html" style="color:var(--c-muted)">mediacriticinc@gmail.com</a></p>
</div>
</footer>
<script>
document.querySelectorAll('.pal-btn').forEach(function(b){{
  b.addEventListener('click',function(){{
    document.querySelectorAll('.pal-btn').forEach(function(x){{x.classList.remove('active');}});
    b.classList.add('active');
    var fam=b.dataset.fam;
    document.querySelectorAll('.rank-row').forEach(function(r){{
      r.style.display=(fam==='tous'||r.dataset.fam===fam)?'flex':'none';
    }});
  }});
}});
</script>
</body>
</html>
"""
    (ROOT / "palmares.html").write_text(page, encoding="utf-8")
    print(f"palmares.html généré — {len(rows)} entrées, podium : "
          + ", ".join(f'{r["title"]} {r["note"]}' for r in rows[:3]))

if __name__ == "__main__":
    build()
