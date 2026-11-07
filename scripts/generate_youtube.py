#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genere chaines-youtube.html : l'annuaire des chaines YouTube francophones
(vague 2 SEO, 07/11/2026). « annuaire youtube » etait le theme le plus faible
de l'audit d'octobre : aucune page n'etait consacree aux 1 600+ chaines,
noyees dans l'annuaire general.

Sections, toutes calculees sur les donnees reelles (abonnes YouTube, notes
MediaCritic) : les plus suivies, les independantes, celles critiquees par
MediaCritic, puis un top 10 par theme.

Dans REGENERATEURS et dans enrich.yml.
Usage : python scripts/generate_youtube.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charte import appliquer as charte_appliquer  # noqa: E402
from generate_classement import _css, _nombre, h, section  # noqa: E402

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"
PAGE = "chaines-youtube.html"
THEMES = [  # (slug d'ancre, titre, categories)
    ("gaming", "jeu vidéo", {"gaming", "jeux"}),
    ("humour", "humour", {"humour", "comedie"}),
    ("histoire", "histoire", {"histoire"}),
    ("sciences", "sciences", {"sciences", "education"}),
    ("tech", "tech", {"tech", "numerique"}),
    ("cuisine", "cuisine", {"gastronomie", "cuisine"}),
    ("sport", "sport", {"sport", "football", "fitness"}),
    ("musique", "musique", {"musique"}),
    ("cinema", "cinéma et séries", {"cinema", "series"}),
    ("culture", "culture", {"culture", "arts", "livres"}),
]


def abonnes(x):
    n = int(x["subscribers"])
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}".replace(".", ",").replace(",0", "") + " M"
    return f"{round(n / 1000)} k" if n >= 1000 else str(n)


def main():
    cat = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    yt = [x for x in cat if x.get("type") == "youtube" and x.get("subscribers")]
    yt.sort(key=lambda x: -int(x["subscribers"]))
    indep = [x for x in yt if x.get("independant")]
    critiquees = sorted([x for x in cat if x.get("type") == "youtube" and x.get("mcNote")],
                        key=lambda x: (-float(x["mcNote"]), x.get("title", "").lower()))

    specs = [
        ("plus-suivies", "Les chaînes YouTube francophones les plus suivies",
         f"Les 50 premières par nombre d'abonnés, parmi les {_nombre(len(yt))} chaînes de l'annuaire.",
         yt[:50], abonnes, "abonnés"),
        ("independantes", "Les chaînes YouTube indépendantes les plus suivies",
         "Des créateurs et de petites structures : ni médias, ni marques, ni maisons de disques. "
         "<a href=\"podcasts-independants.html\">Le guide des indépendants</a>.",
         indep[:30], abonnes, "abonnés"),
        ("critiquees", "Les chaînes YouTube critiquées par MediaCritic",
         "Celles que nous avons regardées, analysées et notées dans le podcast.",
         critiquees, lambda x: str(x["mcNote"]).replace(".", ","), "sur 10 · MediaCritic"),
    ]
    for ancre, nom, cats in THEMES:
        liste = [x for x in yt if set(x.get("categories") or []) & cats][:10]
        if len(liste) >= 5:
            specs.append((ancre, f"Les meilleures chaînes YouTube {nom}",
                          f"Classées par nombre d'abonnés.", liste, abonnes, "abonnés"))

    sections, listes, sommaire = [], [], []
    for args in specs:
        bloc, ld = section(*args)
        if bloc:
            # section() echappe le chapo : on y autorise notre seul lien interne.
            bloc = bloc.replace("&lt;a href=&quot;podcasts-independants.html&quot;&gt;",
                                '<a href="podcasts-independants.html">').replace("&lt;/a&gt;", "</a>")
            sections.append(bloc)
            listes.append(ld)
            court = {"plus-suivies": "Les plus suivies", "independantes": "Indépendantes",
                     "critiquees": "Critiquées par MediaCritic"}.get(
                args[0], args[1].replace("Les meilleures chaînes YouTube ", "").capitalize())
            sommaire.append(f'<a href="#{args[0]}">{h(court)}</a>')

    titre = "Annuaire des chaînes YouTube francophones | MediaCritic"
    desc = (f"L'annuaire de {_nombre(len(yt) // 100 * 100)}+ chaînes YouTube francophones : les plus "
            f"suivies, les indépendantes, les meilleures par thème et nos critiques.")
    ld = {"@context": "https://schema.org", "@graph": listes + [
        {"@type": "CollectionPage", "@id": f"{BASE}/{PAGE}", "url": f"{BASE}/{PAGE}",
         "name": "Annuaire des chaînes YouTube francophones", "description": desc,
         "inLanguage": "fr-FR", "isPartOf": {"@id": BASE + "/#annuaire"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Annuaire", "item": f"{BASE}/catalogue.html"},
            {"@type": "ListItem", "position": 3, "name": "Chaînes YouTube", "item": f"{BASE}/{PAGE}"}]},
    ]}
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(titre)}</title>
<meta name="description" content="{h(desc)}" />
<meta name="keywords" content="annuaire youtube, annuaire des chaînes YouTube francophones, meilleures chaînes YouTube françaises, chaînes YouTube indépendantes, critique youtube" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{BASE}/{PAGE}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE}/{PAGE}" />
<meta property="og:title" content="{h(titre)}" />
<meta property="og:description" content="{h(desc)}" />
<meta property="og:image" content="{BASE}/assets/banner.png" />
<meta name="twitter:card" content="summary_large_image" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{_css()}
<style>
.cl-section{{max-width:820px;margin:0 auto 52px;padding:0 clamp(16px,4vw,32px)}}
.cl-chapo{{color:var(--c-muted);font-size:.9rem;line-height:1.6;margin-bottom:20px}}
.cl-chapo a{{color:var(--mc-text);text-decoration:underline}}
.cl-list{{list-style:none;display:flex;flex-direction:column;gap:2px}}
.cl-item{{display:flex;align-items:center;gap:12px;padding:9px 10px;border-radius:10px}}
.cl-item:hover{{background:rgba(255,255,255,.04)}}
.cl-rang{{flex:0 0 30px;text-align:right;font-weight:700;color:var(--c-muted2);font-size:.95rem}}
.cl-lien{{flex:1;display:flex;align-items:center;gap:12px;min-width:0}}
.cl-cover{{flex:0 0 44px;height:44px;border-radius:50%;overflow:hidden;background:#13233b;display:flex;align-items:center;justify-content:center}}
.cl-cover img{{width:100%;height:100%;object-fit:cover;display:block}}
.cl-ph{{font-weight:700;color:rgba(255,255,255,.5);font-size:.85rem}}
.cl-txt{{min-width:0;display:flex;flex-direction:column}}
.cl-titre{{font-weight:600;font-size:.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cl-item:hover .cl-titre{{color:var(--c-orange)}}
.cl-auteur{{display:none}}
.cl-val{{flex:0 0 auto;text-align:right;font-weight:700;font-size:.95rem;display:flex;flex-direction:column;line-height:1.2}}
.cl-leg{{font-size:.66rem;font-weight:500;color:var(--c-muted);text-transform:uppercase;letter-spacing:.05em}}
.cl-mc{{display:none}}
.cl-intro{{max-width:820px;margin:0 auto 36px;padding:0 clamp(16px,4vw,32px)}}
.cl-intro p{{color:var(--c-muted);line-height:1.7;margin-bottom:12px}}
.cl-intro p a{{color:var(--mc-text);text-decoration:underline}}
.cl-somm{{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}}
.cl-somm a{{font-size:.8rem;font-weight:600;padding:6px 14px;border-radius:99px;background:var(--c-glass);border:1px solid var(--c-border);color:var(--c-muted2)}}
@media(max-width:520px){{.cl-cover{{flex:0 0 36px;height:36px}}.cl-rang{{flex:0 0 22px;font-size:.85rem}}}}
</style>
</head>
<body>
<nav></nav>
<header class="cl-intro">
  <h1>L'annuaire des chaînes YouTube francophones</h1>
  <p><strong>{_nombre(len(yt))}</strong> chaînes YouTube de langue française référencées dans
  <a href="catalogue.html">l'annuaire MediaCritic</a>, aux côtés des podcasts : gaming, humour,
  histoire, sciences, tech, cuisine, sport… Classées par nombre d'abonnés, avec les chaînes
  indépendantes et celles que nous avons critiquées dans notre podcast. Mis à jour
  automatiquement.</p>
  <div class="cl-somm">{"".join(sommaire)}</div>
</header>
{"".join(sections)}
<footer></footer>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>
<script defer src="/assets/partage.js"></script>
</body>
</html>"""
    page, etat = charte_appliquer(page, "annuaire")
    assert etat is not None, "charte non appliquée"
    (ROOT / PAGE).write_text(page, encoding="utf-8")
    print(f"{PAGE} généré — {len(yt)} chaînes, {len(sections)} sections")


if __name__ == "__main__":
    main()
