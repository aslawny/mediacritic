#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genere podcasts-independants.html : le guide des podcasts independants.

L'expression « guide des podcasts independants » figurait dans les balises
du catalogue sans qu'aucune page ne la porte (remarque d'un relecteur,
24/10/2026). Cette page la rend reelle.

Definition validee par l'utilisateur : un podcast est independant s'il
n'est publie ni par un media (radio, television, presse), ni par une
institution ou une marque, ni par un studio ou un reseau de podcasts
professionnel. Podcasts seulement : sur YouTube, presque tout est
independant, le filtre n'apprendrait rien.

La seule donnee disponible est le nom de l'editeur (champ author) : le
tri est donc une exclusion par liste et par mots-cles. Il ne peut pas etre
parfait, la page le dit et invite a signaler une erreur. Les listes
affichees (une centaine de lignes) se relisent a la main apres toute
modification de EDITEURS_EXCLUS ou MOTS_EXCLUS.

Usage : python scripts/generate_independants.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charte import appliquer as charte_appliquer  # noqa: E402
from generate_classement import _css, _nombre, h, section  # noqa: E402
from independance import est_independant  # noqa: E402  source unique

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"
PAGE = "podcasts-independants.html"
# Les independants ont moins d'avis que les grandes radios : le plancher
# du classement general (500) n'en laisserait presque aucun.
PLANCHER_AVIS = 100
M_BAYES = 100
TAILLE = 50


def main():
    cat = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    pods = [x for x in cat if x.get("type") != "youtube"]
    indep = [x for x in pods if est_independant(x)]
    # Chaines YouTube : etendu le 25/10/2026 (meme definition, voir independance.py).
    yts = [x for x in cat if x.get("type") == "youtube"]
    indep_yt = [x for x in yts if est_independant(x)]
    chaines = sorted([x for x in indep_yt if x.get("subscribers")],
                     key=lambda x: -int(x["subscribers"]))[:TAILLE]
    notes = [x for x in indep if x.get("rating") and x.get("ratingCount")]
    moyenne = sum(float(x["rating"]) for x in notes) / max(1, len(notes))

    def bayes(x):
        v = int(x["ratingCount"])
        return (v / (v + M_BAYES)) * float(x["rating"]) + (M_BAYES / (v + M_BAYES)) * moyenne

    eligibles = [x for x in notes if int(x["ratingCount"]) >= PLANCHER_AVIS]
    mieux_notes = sorted(eligibles, key=lambda x: -bayes(x))[:TAILLE]
    populaires = sorted(notes, key=lambda x: -int(x["ratingCount"]))[:TAILLE]
    pepites = sorted([x for x in indep + indep_yt if x.get("mcNote")],
                     key=lambda x: (-float(x["mcNote"]), x.get("title", "").lower()))

    sections, listes = [], []
    for args in (
        ("mieux-notes", "Les podcasts indépendants les mieux notés",
         f"Note Apple Podcasts, parmi les {len(eligibles)} podcasts indépendants comptant "
         f"au moins {PLANCHER_AVIS} avis. En dessous, une moyenne parfaite ne veut rien dire.",
         mieux_notes, lambda x: f'{float(x["rating"]):.1f}'.replace(".", ","),
         "sur 5 · Apple"),
        ("populaires", "Les podcasts indépendants les plus écoutés",
         "Classés par nombre d'avis déposés sur Apple Podcasts, la mesure la plus "
         "objective de l'audience d'un podcast.", populaires,
         lambda x: _nombre(x["ratingCount"]), "avis Apple"),
        ("chaines", "Les chaînes YouTube indépendantes les plus suivies",
         f"Classées par nombre d'abonnés, parmi les {_nombre(len(indep_yt))} chaînes "
         "indépendantes de l'annuaire.", chaines,
         lambda x: _nombre(x["subscribers"]), "abonnés"),
        ("pepites", "Les indépendants analysés par MediaCritic",
         "Ceux que nous avons écoutés, critiqués et notés dans le podcast. "
         "Notre avis, pas celui d'un algorithme.", pepites,
         lambda x: str(x["mcNote"]).replace(".", ","), "sur 10 · MediaCritic"),
    ):
        bloc, ld = section(*args)
        if bloc:
            sections.append(bloc)
            listes.append(ld)

    titre = "Podcasts et chaînes YouTube indépendants"
    desc = (f"Le guide des indépendants : {_nombre(len(indep))} podcasts et "
            f"{_nombre(len(indep_yt))} chaînes YouTube francophones hors médias, studios "
            f"et marques, classés par note et par audience.")

    ld = {"@context": "https://schema.org", "@graph": listes + [
        {"@type": "CollectionPage", "@id": f"{BASE}/{PAGE}", "url": f"{BASE}/{PAGE}",
         "name": titre, "description": desc, "inLanguage": "fr-FR",
         "isPartOf": {"@id": BASE + "/#annuaire"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Annuaire",
             "item": f"{BASE}/catalogue.html"},
            {"@type": "ListItem", "position": 3, "name": "Indépendants",
             "item": f"{BASE}/{PAGE}"}]},
    ]}

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(titre)} | MediaCritic</title>
<meta name="description" content="{h(desc)}" />
<meta name="keywords" content="guide des podcasts indépendants, chaînes YouTube indépendantes, podcasts indépendants francophones, podcast indépendant, annuaire podcast francophone, meilleurs podcasts indépendants" />
<meta name="robots" content="index, follow" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
<link rel="canonical" href="{BASE}/{PAGE}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE}/{PAGE}" />
<meta property="og:title" content="{h(titre)}" />
<meta property="og:description" content="{h(desc)}" />
<meta property="og:image" content="{BASE}/assets/banner.png" />
<meta property="og:locale" content="fr_FR" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{h(titre)} — MediaCritic" />
<meta name="twitter:description" content="{h(desc)}" />
<meta name="twitter:image" content="{BASE}/assets/banner.png" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{_css()}
<style>
.cl-section{{max-width:820px;margin:0 auto 52px;padding:0 clamp(16px,4vw,32px)}}
.cl-chapo{{color:var(--c-muted);font-size:.9rem;line-height:1.6;margin-bottom:20px}}
.cl-list{{list-style:none;display:flex;flex-direction:column;gap:2px}}
.cl-item{{display:flex;align-items:center;gap:12px;padding:9px 10px;border-radius:10px;transition:background .18s}}
.cl-item:hover{{background:rgba(255,255,255,.04)}}
.cl-rang{{flex:0 0 30px;text-align:right;font-weight:700;color:var(--c-muted2);font-size:.95rem}}
.cl-lien{{flex:1;display:flex;align-items:center;gap:12px;min-width:0}}
.cl-cover{{flex:0 0 44px;height:44px;border-radius:8px;overflow:hidden;background:linear-gradient(135deg,#1a2030,#0d1220);display:flex;align-items:center;justify-content:center}}
.cl-cover img{{width:100%;height:100%;object-fit:cover;display:block}}
.cl-ph{{font-weight:700;color:rgba(255,255,255,.5);font-size:.85rem}}
.cl-txt{{min-width:0;display:flex;flex-direction:column}}
.cl-titre{{font-weight:600;font-size:.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cl-item:hover .cl-titre{{color:var(--c-orange)}}
.cl-auteur{{font-size:.75rem;color:var(--c-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cl-val{{flex:0 0 auto;text-align:right;font-weight:700;font-size:.95rem;display:flex;flex-direction:column;line-height:1.2}}
.cl-leg{{font-size:.66rem;font-weight:500;color:var(--c-muted);text-transform:uppercase;letter-spacing:.05em}}
.cl-mc{{display:none}}
.cl-intro{{max-width:820px;margin:0 auto 40px;padding:0 clamp(16px,4vw,32px)}}
.cl-intro p{{color:var(--c-muted);line-height:1.7;margin-bottom:12px}}
.cl-intro p a{{color:var(--mc-text);text-decoration:underline;text-underline-offset:2px}}
.cl-somm{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}}
.cl-somm a{{font-size:.8rem;font-weight:600;padding:6px 14px;border-radius:99px;background:var(--c-glass);border:1px solid var(--c-border);color:var(--c-muted2)}}
.cl-somm a:hover{{border-color:rgba(232,98,45,.4);color:var(--c-text)}}
@media(max-width:520px){{.cl-cover{{flex:0 0 36px;height:36px}}.cl-rang{{flex:0 0 22px;font-size:.85rem}}}}
</style>
</head>
<body>
<nav></nav>
<header class="cl-intro">
  <h1>Le guide des podcasts et chaînes YouTube indépendants</h1>
  <p>Dans <a href="catalogue.html">notre annuaire</a>, <strong>{_nombre(len(indep))}</strong>
  podcasts sur {_nombre(len(pods))} et <strong>{_nombre(len(indep_yt))}</strong> chaînes
  YouTube sur {_nombre(len(yts))} sont indépendants : ils ne sont publiés ni par une radio,
  une télévision ou un titre de presse, ni par une institution, un club ou une marque, ni par
  un studio, un réseau ou une maison de disques. Des créateurs et de petites structures,
  souvent sans budget de promotion, que les classements des plateformes laissent dans
  l'ombre des grands médias.</p>
  <p>Le tri se fait sur le nom de l'éditeur ou de la chaîne. Il peut se tromper :
  si un contenu est mal classé, <a href="contact.html">dites-le-nous</a>. Les notes et les
  audiences des podcasts viennent d'Apple Podcasts, celles des chaînes de YouTube ; les
  pépites, de nos propres critiques. Mis à jour automatiquement.</p>
  <div class="cl-somm">
    <a href="#mieux-notes">Les mieux notés</a>
    <a href="#populaires">Les plus écoutés</a>
    <a href="#chaines">Chaînes YouTube</a>
    <a href="#pepites">Analysés par MediaCritic</a>
    <a href="classement.html">Classement général</a>
  </div>
</header>
{"".join(sections)}
<footer></footer>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>
<script defer src="/assets/partage.js"></script>
</body>
</html>"""

    page, etat = charte_appliquer(page, "independants")
    assert etat is not None, "charte non appliquee (en-tete ou pied introuvable)"
    (ROOT / PAGE).write_text(page, encoding="utf-8")
    print(f"{PAGE} généré — {len(indep)} indépendants sur {len(pods)} podcasts ; "
          f"{len(mieux_notes)} mieux notés ({len(eligibles)} éligibles), "
          f"{len(populaires)} populaires, {len(pepites)} pépites")


if __name__ == "__main__":
    main()
