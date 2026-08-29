#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère des pages catégories statiques (SEO) à partir de data/catalog.json,
sur le modèle des pages existantes (categories/gaming.html, etc.).

Chaque page liste : les contenus analysés par MediaCritic (en avant), puis
le reste des contenus de la catégorie (cap 80), avec un texte d'intro, une
FAQ et un JSON-LD ItemList. Le CSS/nav/footer sont repris d'une page modèle.

Usage : python scripts/generate_categories.py
"""
import json, re, html, subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
CATALOG = ROOT / "data" / "catalog.json"
OUT = ROOT / "categories"
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"
MONTH = "juin 2026"
MAX_OTHERS = 80

# CSS partagé : extrait d'une page modèle (déterministe, via git)
_model = subprocess.run(
    ["git", "show", "HEAD:categories/gaming.html"],
    cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
).stdout
CSS = re.search(r"<style>.*?</style>", _model, re.DOTALL).group(0)

BURGER_BTN = ('<button class="nav-burger" aria-label="Ouvrir le menu" aria-expanded="false" '
              'onclick="var l=document.querySelector(\'.nav-links\');l.classList.toggle(\'open\');'
              'this.setAttribute(\'aria-expanded\',l.classList.contains(\'open\'));">☰</button>')

BURGER_CSS = """<style>/* mc-burger : menu mobile */
.nav-burger{display:none;background:none;border:1px solid rgba(255,255,255,.15);color:inherit;font-size:1.05rem;line-height:1;padding:6px 11px;border-radius:8px;cursor:pointer}
@media(max-width:640px){
.nav-burger{display:block}
.nav-links{display:none;position:absolute;top:100%;left:0;right:0;background:rgba(6,11,20,.98);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.08);flex-direction:column;align-items:stretch;padding:10px 16px 14px;gap:4px;z-index:400}
.nav-links.open{display:flex}
.nav-links a{padding:10px 12px;font-size:.92rem}
}</style>"""

def h(s):
    return html.escape(str(s or ""), quote=True)

# ─── Config des catégories à générer ──────────────────────────────────────────
# slug = nom de fichier ; cats = catégories du catalogue à inclure
CATEGORIES = [
    {
        "slug": "histoire", "cats": ["histoire"], "name": "Histoire", "emoji": "📜",
        "title": "Meilleurs podcasts d'histoire francophones — 2026",
        "h1": "Les meilleurs podcasts d'histoire francophones",
        "lede": "L'histoire est l'une des catégories les plus saturées du podcast francophone — et l'une des plus inégales. Entre les vulgarisateurs YouTube qui passent au podcast, les historiens de métier qui s'essaient au micro et les médias publics qui produisent des séries léchées, comment faire le tri ? MediaCritic a écouté et analysé en détail plusieurs références du genre.",
        "faq": [
            ("Quel est le meilleur podcast d'histoire francophone pour débuter ?", "Pour s'initier, Nota Bene et Quelle Histoire sont accessibles, bien produits, et adoptent un ton vulgarisateur sans être condescendants. Entrez dans l'Histoire offre une approche plus immersive, et C'est plus compliqué que ça pousse plus loin la nuance pour les auditeurs déjà familiers du genre."),
            ("Les podcasts d'histoire sont-ils fiables historiquement ?", "Cela dépend du créateur. Les podcasts d'historiens diplômés (Nota Bene a un comité scientifique, certaines productions Radio France collaborent avec des chercheurs) sont en général solides. Méfiez-vous des podcasts qui ne citent jamais leurs sources."),
        ],
    },
    {
        "slug": "gaming", "cats": ["gaming"], "name": "Gaming", "emoji": "🎮",
        "title": "Meilleurs podcasts gaming et chaînes YouTube jeu vidéo francophones — 2026",
        "h1": "Les meilleurs podcasts et chaînes YouTube gaming francophones",
        "lede": "Le gaming est la catégorie où l'audio et la vidéo se mélangent le plus : entre les podcasts de discussion long-format, les chaînes YouTube qui font de l'analyse pure, et les hybrides en live sur Twitch reuploadés en podcast, il y a de tout — et beaucoup de redondance. MediaCritic a analysé plusieurs références du paysage français.",
        "faq": [
            ("Quelle est la meilleure chaîne YouTube gaming française ?", "Le Joueur du Grenier reste la référence sans équivalent en termes de longévité (depuis 2009) et d'audience. Mais pour l'analyse pure, des chaînes plus récentes offrent une approche éditoriale différente."),
            ("Comment MediaCritic note-t-il les podcasts gaming ?", "Comme tous les autres : fond (qualité de l'analyse, des sources, des opinions), forme (montage, rythme, son), intentions (clarté du positionnement éditorial). Le format YouTube est traité avec les mêmes critères que le podcast audio."),
        ],
    },
    {
        "slug": "tech", "cats": ["tech", "numerique"], "name": "Tech", "emoji": "💻",
        "title": "Meilleurs podcasts tech francophones — 2026",
        "h1": "Les meilleurs podcasts tech francophones",
        "lede": "Le podcast tech francophone se partage entre trois familles : les podcasts d'actualité (Le Rendez-vous Tech), les podcasts d'opinion (Silicon Carne), et les podcasts métier pour développeurs (IFTTD, Hardisk Stories). MediaCritic a analysé les références de chaque famille.",
        "faq": [
            ("Quel podcast tech écouter pour rester à jour ?", "Pour l'actualité large et grand public, Le Rendez-vous Tech reste la référence. Pour un ton plus tranché et une vraie opinion éditoriale, Silicon Carne. Pour le détail technique côté dev, IFTTD - If This Then Dev."),
            ("MediaCritic est-il un podcast tech ?", "Non. MediaCritic est un podcast de méta-analyse qui décortique d'autres podcasts et chaînes YouTube — toutes catégories confondues. Le tech est l'une des nombreuses verticales qu'on analyse régulièrement."),
        ],
    },
    {
        "slug": "sport", "cats": ["sport", "football", "basket", "nba", "running", "endurance", "fitness"],
        "name": "Sport", "emoji": "🏅",
        "title": "Meilleurs podcasts sport francophones — 2026",
        "h1": "Les meilleurs podcasts sport francophones",
        "lede": "Le podcast sport francophone, c'est encore largement le football. Mais des formats émergent autour du trail, du running, des sports outdoor, et des conversations plus larges sur la performance et la santé sportive. MediaCritic a analysé plusieurs références complémentaires.",
        "faq": [
            ("Quel est le meilleur podcast football en français ?", "L'After Foot (RMC) reste la référence par sa longévité et son audience, mais le format radio peut peser. Pour du long-format plus posé, des podcasts indépendants émergent — le catalogue MediaCritic en référence plusieurs."),
            ("Y a-t-il des podcasts running ou trail à recommander ?", "Oui. SafePace propose un format accessible autour du running. Extraterrien creuse les disciplines d'ultra-endurance avec des interviews approfondies d'athlètes."),
        ],
    },
    {
        "slug": "cuisine-gastronomie", "cats": ["cuisine", "gastronomie"], "name": "Cuisine &amp; gastronomie", "emoji": "🍽️",
        "title": "Meilleurs podcasts cuisine et gastronomie francophones — 2026",
        "h1": "Les meilleurs podcasts cuisine et gastronomie francophones",
        "lede": "La cuisine est la catégorie qui a le plus explosé sur les plateformes audio ces trois dernières années. Entre les chefs qui se lancent, les food writers qui réfléchissent l'alimentation, et les podcasts conversationnels autour de la table, il y a de quoi trier. MediaCritic a décortiqué Chef Otaku (la passion technique) et On va déguster (l'institution France Inter).",
        "faq": [
            ("Quel est le meilleur podcast pour apprendre la cuisine ?", "Pour l'apprentissage technique, les podcasts de chefs comme Chef Otaku sont précieux car ils expliquent les gestes, les choix, les erreurs à éviter. Pour la culture culinaire générale, On va déguster reste une référence — moins technique, plus contextuelle."),
            ("Y a-t-il des podcasts gastronomie indépendants à découvrir ?", "Oui, beaucoup. Le catalogue MediaCritic référence de nombreux podcasts cuisine et gastronomie, incluant des indépendants méconnus mais excellents."),
        ],
    },
    {
        "slug": "true-crime", "cats": ["true crime"], "name": "True Crime", "emoji": "🔍",
        "title": "Meilleurs podcasts true crime francophones — 2026",
        "h1": "Les meilleurs podcasts true crime francophones",
        "lede": "Le true crime est l'un des genres les plus écoutés du podcast francophone : affaires criminelles, disparitions, enquêtes non résolues, profils de tueurs… Voici les podcasts true crime de référence, des grands formats journalistiques aux récits plus intimes.",
        "faq": [
            ("C'est quoi un podcast true crime ?", "Un podcast true crime raconte des affaires criminelles réelles : meurtres, disparitions, enquêtes judiciaires, parfois résolues, parfois non. Le genre mêle journalisme d'investigation, narration immersive et analyse."),
            ("Quels sont les meilleurs podcasts true crime français ?", "Parmi les références francophones, on retrouve des formats produits par de grands médias comme par des indépendants. Les contenus analysés par MediaCritic sont mis en avant en haut de cette page."),
        ],
    },
    {
        "slug": "sciences", "cats": ["sciences", "vulgarisation"], "name": "Sciences", "emoji": "🔬",
        "title": "Meilleurs podcasts sciences et vulgarisation francophones — 2026",
        "h1": "Les meilleurs podcasts sciences et vulgarisation francophones",
        "lede": "Physique, biologie, espace, climat, neurosciences… La vulgarisation scientifique francophone est riche, du grand format pédagogique aux pastilles courtes. Voici les podcasts et chaînes qui rendent la science accessible et passionnante.",
        "faq": [
            ("Quel podcast pour apprendre des sciences ?", "Les podcasts de vulgarisation scientifique permettent de comprendre des sujets complexes sans bagage technique. Cette page référence les meilleurs formats francophones, classés et notés."),
            ("Podcast ou chaîne YouTube pour la science ?", "Les deux : certains créateurs privilégient l'audio long-format, d'autres la vidéo avec schémas et animations. MediaCritic référence et analyse les deux."),
        ],
    },
    {
        "slug": "business", "cats": ["business", "entrepreneuriat", "economie"], "name": "Business", "emoji": "💼",
        "title": "Meilleurs podcasts business, entrepreneuriat et économie francophones — 2026",
        "h1": "Les meilleurs podcasts business et entrepreneuriat francophones",
        "lede": "Entrepreneuriat, finance, stratégie, économie, parcours de fondateurs… Le business est l'une des catégories les plus fournies du podcast francophone. Voici les formats de référence pour apprendre, s'inspirer et décrypter le monde de l'entreprise.",
        "faq": [
            ("Quel podcast pour entreprendre ?", "Les podcasts d'entrepreneuriat partagent des parcours, des méthodes et des retours d'expérience de fondateurs et dirigeants. Cette page liste les meilleurs formats francophones."),
            ("Quels podcasts pour comprendre l'économie ?", "Plusieurs podcasts décryptent l'actualité économique et financière de façon accessible. Les contenus analysés par MediaCritic sont signalés en haut de page."),
        ],
    },
    {
        "slug": "cinema-series", "cats": ["cinema", "series"], "name": "Cinéma & séries", "emoji": "🎬",
        "title": "Meilleurs podcasts cinéma et séries francophones — 2026",
        "h1": "Les meilleurs podcasts cinéma et séries francophones",
        "lede": "Critiques de films, analyses de séries, histoire du 7e art, coulisses et recommandations… Voici les podcasts et chaînes francophones incontournables pour les passionnés de cinéma et de séries.",
        "faq": [
            ("Quel podcast pour les amateurs de cinéma ?", "Du débat critique à l'analyse de fond, les podcasts cinéma francophones couvrent tous les styles. Cette page référence les meilleurs, avec le badge MediaCritic pour ceux qu'on a analysés."),
            ("Y a-t-il des podcasts dédiés aux séries ?", "Oui, de nombreux formats suivent l'actualité des séries, décryptent les sorties et reviennent sur les classiques. Ils sont référencés ici."),
        ],
    },
    {
        "slug": "culture-societe", "cats": ["culture", "societe"], "name": "Culture & société", "emoji": "🌍",
        "title": "Meilleurs podcasts culture et société francophones — 2026",
        "h1": "Les meilleurs podcasts culture et société francophones",
        "lede": "Idées, débats, faits de société, philosophie, arts… La culture et la société forment la catégorie la plus vaste du podcast francophone. Voici une sélection des formats qui éclairent le monde et nourrissent la réflexion.",
        "faq": [
            ("Quels sont les meilleurs podcasts de société ?", "Les podcasts culture et société abordent les grandes questions contemporaines avec recul et profondeur. Cette page met en avant les références francophones."),
            ("Podcast culture : par où commencer ?", "Commencez par les contenus analysés par MediaCritic, signalés en haut de page, puis explorez le reste du catalogue référencé."),
        ],
    },
    {
        "slug": "musique", "cats": ["musique"], "name": "Musique", "emoji": "🎵",
        "title": "Meilleurs podcasts musique francophones — 2026",
        "h1": "Les meilleurs podcasts musique francophones",
        "lede": "Histoire des genres, portraits d'artistes, décryptage de morceaux, actualité musicale… Voici les podcasts et chaînes francophones pour les mélomanes, du rap au classique en passant par la pop et l'électro.",
        "faq": [
            ("Quel podcast pour les passionnés de musique ?", "Les podcasts musique vont du documentaire sonore au talk entre passionnés. Cette page référence les meilleurs formats francophones, notés et classés."),
            ("Des podcasts sur un genre musical précis ?", "Oui, beaucoup se spécialisent (rap, jazz, électro, classique…). Utilisez le catalogue complet pour affiner par thème."),
        ],
    },
    {
        "slug": "humour", "cats": ["humour", "comedie"], "name": "Humour", "emoji": "😄",
        "title": "Meilleurs podcasts et chaînes humour francophones — 2026",
        "h1": "Les meilleurs podcasts et chaînes humour francophones",
        "lede": "Stand-up, talk décalés, sketchs, comédie… L'humour est partout dans le podcast et sur YouTube francophone. Voici les formats qui font rire, du grand n'importe quoi assumé à la satire fine.",
        "faq": [
            ("Quel podcast humour écouter ?", "Des talks délirants aux formats plus écrits, l'humour francophone est très riche en podcast comme sur YouTube. Cette page liste les références."),
            ("Podcast ou chaîne YouTube pour l'humour ?", "Les deux formats sont représentés ici. Les contenus analysés par MediaCritic apparaissent en premier."),
        ],
    },
    {
        "slug": "voyage", "cats": ["voyage"], "name": "Voyage", "emoji": "🌍",
        "title": "Meilleurs podcasts de voyage francophones — 2026",
        "h1": "Les meilleurs podcasts de voyage francophones",
        "lede": "Récits d'aventure, carnets de route, conseils pratiques, portraits de grands voyageurs… Le voyage est l'une des catégories les plus vivantes du podcast francophone, et l'une des plus inégales : entre le journal de bord bricolé et le documentaire sonore ciselé, l'écart est immense. Voici les formats qui donnent vraiment envie de partir.",
        "faq": [
            ("Quel podcast de voyage écouter avant de partir ?", "Selon ce que vous cherchez : les podcasts de récit racontent une aventure de bout en bout, les formats pratiques préparent un itinéraire précis. Cette page référence les deux familles, notées et classées."),
            ("Des podcasts sur une destination précise ?", "Beaucoup se consacrent à une région ou à un type de voyage (randonnée, tour du monde, voyage en famille…). Le catalogue complet permet d'affiner."),
        ],
    },
]

# Liens croisés : toutes les pages catégories (existantes + nouvelles)
ALL_PAGES = [
    ("histoire", "Histoire"), ("gaming", "Gaming"), ("tech", "Tech"),
    ("sport", "Sport"), ("cuisine-gastronomie", "Cuisine &amp; gastronomie"),
    ("true-crime", "True Crime"), ("sciences", "Sciences"), ("business", "Business"),
    ("cinema-series", "Cinéma &amp; séries"), ("culture-societe", "Culture &amp; société"),
    ("musique", "Musique"), ("humour", "Humour"), ("voyage", "Voyage"),
]

def card(item):
    cls = "c-card mc" if item.get("hasMediacritic") else "c-card"
    slug = item["slug"]
    img = item.get("image")
    if img:
        cover = f'<div class="card-cover"><img src="{h(img)}" alt="{h(item.get("title"))}" loading="lazy" decoding="async"></div>'
    else:
        emoji = "📺" if item.get("type") == "youtube" else "🎙️"
        cover = f'<div class="card-cover"><div class="card-cover-ph">{emoji}</div></div>'
    badge = ""
    if item.get("hasMediacritic") and item.get("mcEpisode"):
        badge = f'<span class="mc-badge">MC Ép.{item["mcEpisode"]}</span>'
    cover = cover.replace("</div>", badge + "</div>", 1) if badge else cover
    cat0 = h((item.get("categories") or [""])[0])
    author = f'<div class="card-author">{h(item.get("author"))}</div>' if item.get("author") else ""
    return (f'<a class="{cls}" href="../fiches/{h(slug)}.html">{cover}'
            f'<div class="card-body"><div class="card-title">{h(item.get("title"))}</div>'
            f'{author}<div class="card-meta"><span class="card-cat">{cat0}</span></div></div></a>')

def sort_key(x):
    return (1 if x.get("rating") else 0, x.get("rating") or 0,
            x.get("subscribers") or 0, x.get("ratingCount") or 0)

def build_page(cfg, catalog):
    cats = set(cfg["cats"])
    items = [x for x in catalog if cats & set(x.get("categories") or [])]
    mc = sorted([x for x in items if x.get("hasMediacritic")],
                key=lambda x: x.get("mcEpisode") or 999)
    others = sorted([x for x in items if not x.get("hasMediacritic")],
                    key=sort_key, reverse=True)[:MAX_OTHERS]
    total = len(items)
    shown_others = others

    mc_titles = ", ".join(x["title"] for x in mc[:5])
    # « Annuaire » en tete : ces 13 pages sont indexees et portent, elles aussi,
    # l identite d annuaire -- pas seulement celle d un blog de critiques.
    desc = f'Annuaire de {total}+ podcasts et chaînes YouTube {cfg["name"].lower()} francophones'
    if mc:
        desc += f', dont {len(mc)} analysé{"s" if len(mc)>1 else ""} par MediaCritic : {mc_titles}.'
    else:
        desc += ', référencés, notés et classés par MediaCritic.'

    # JSON-LD ItemList (MC d'abord, puis autres, max 30)
    ld_items = (mc + shown_others)[:30]
    elements = [{"@type": "ListItem", "position": i + 1,
                 "item": {"@type": "PodcastSeries", "name": x["title"],
                          "url": f'{BASE}/fiches/{x["slug"]}.html'}}
                for i, x in enumerate(ld_items)]
    # isPartOf rattache la page a l annuaire declare sur l accueil : sans ce
    # lien, chaque page categorie n est qu une liste isolee aux yeux d un moteur.
    itemlist = {"@context": "https://schema.org", "@graph": [
        {"@type": "ItemList", "name": cfg["h1"], "numberOfItems": len(elements),
         "itemListElement": elements,
         "isPartOf": {"@id": BASE + "/#annuaire"}},
        {"@type": "DataCatalog", "@id": BASE + "/#annuaire",
         "name": "Annuaire MediaCritic des podcasts et chaînes YouTube francophones",
         "alternateName": ["Annuaire podcast francophone",
                           "Répertoire collaboratif de podcasts",
                           "Le guide des podcasts indépendants"],
         "url": BASE + "/catalogue.html",
         "inLanguage": "fr-FR", "isAccessibleForFree": True},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": cfg["name"],
             "item": f'{BASE}/categories/{cfg["slug"]}.html'}]}]}
    ld = json.dumps(itemlist, ensure_ascii=False)

    mc_section = ""
    if mc:
        mc_section = (f'<section class="podcast-section"><h2>⭐ Analysés en détail par MediaCritic '
                      f'<span class="pill">{len(mc)} épisode{"s" if len(mc)>1 else ""}</span></h2>'
                      f'<div class="grid">{"".join(card(x) for x in mc)}</div></section>')

    # Libellé honnête : on affiche au plus MAX_OTHERS contenus sur le total référencé
    nb_shown = len(mc) + len(shown_others)
    pill = (f"{nb_shown} contenus" if nb_shown >= total
            else f"{nb_shown} affichés sur {total}")
    heading = ("Tous les podcasts" if nb_shown >= total else "Une sélection de podcasts")
    others_section = (f'<section class="podcast-section"><h2>{heading} {cfg["name"].lower()} '
                      f'<span class="pill">{pill}</span></h2>'
                      f'<div class="grid">{"".join(card(x) for x in shown_others)}</div></section>')

    faq = "".join(
        f'<details class="faq-item"><summary>{h(q)}</summary><p>{h(a)}</p></details>'
        for q, a in cfg["faq"])

    cross = "".join(f'<a href="{s}.html">{n}</a>' for s, n in ALL_PAGES if s != cfg["slug"])

    url = f'{BASE}/categories/{cfg["slug"]}.html'
    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(cfg["title"])}</title>
<meta name="description" content="{h(desc)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{url}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{url}" />
<meta property="og:title" content="{h(cfg["title"])}" />
<meta property="og:description" content="{h(desc)}" />
<meta property="og:image" content="{BASE}/assets/banner.png" />
<meta property="og:locale" content="fr_FR" />
<meta property="og:site_name" content="MediaCritic" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@MediaCriticInc" />
<meta name="twitter:title" content="{h(cfg["title"])}" />
<meta name="twitter:description" content="{h(desc)}" />
<meta name="twitter:image" content="{BASE}/assets/banner.png" />
<script type="application/ld+json">{ld}</script>
<link rel="icon" href="../assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
{CSS}
{BURGER_CSS}
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{GA}");</script>
</head>
<body>
<nav>
<a href="../" class="nav-logo"><img src="../assets/logo.png" alt="MediaCritic" /><span>MediaCritic</span></a>
{BURGER_BTN}
<div class="nav-links">
<a href="../">Catalogue</a>
<a href="../palmares.html">Palmarès</a>
<a href="../qui-sommes-nous.html">Qui sommes-nous</a>
<a href="../contact.html">Contact</a>
</div>
<a href="https://open.spotify.com/show/5JuffYLQq1q6l7Vh2zvkrV" target="_blank" rel="noopener noreferrer" class="nav-cta">🎧 Écouter</a>
</nav>
<header class="page-header">
<div class="breadcrumb"><a href="../">MediaCritic</a> · Catégorie · <strong>{h(cfg["name"])}</strong></div>
<h1>{h(cfg["h1"])}</h1>
<p class="lede">{h(cfg["lede"])}</p>
<div class="stat-bar">
<span><span class="num">{total}</span> contenus référencés</span>
<span><span class="num">{len(mc)}</span> analysés par MediaCritic</span>
<span>Mis à jour {MONTH}</span>
</div>
</header>
{mc_section}
{others_section}
<section class="faq">
<h2>Questions fréquentes</h2>
{faq}
</section>
<section class="cross-links">
<h3>Autres catégories</h3>
<div class="cross-links-list">{cross}</div>
</section>
<footer>
<div class="footer-inner">
<div class="footer-logo"><img src="../assets/logo.png" alt="MediaCritic" /><span>MediaCritic</span></div>
<p class="footer-tagline">Le podcast qui donne son avis, même quand on ne lui a pas demandé.</p>
<div class="footer-links">
<a href="../">Catalogue</a>
<a href="../palmares.html">Palmarès</a>
<a href="../qui-sommes-nous.html">Qui sommes-nous</a>
<a href="../contact.html">Contact</a>
</div>
<p class="footer-copy">© 2026 MediaCritic — <a href="../contact.html" style="color:var(--c-muted)">mediacriticinc@gmail.com</a></p>
</div>
</footer>
</body>
</html>
'''

def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    for cfg in CATEGORIES:
        page = build_page(cfg, catalog)
        (OUT / f'{cfg["slug"]}.html').write_text(page, encoding="utf-8")
        n = sum(1 for x in catalog if set(cfg["cats"]) & set(x.get("categories") or []))
        print(f'  {cfg["slug"]}.html  ({n} contenus)')
    print(f'{len(CATEGORIES)} pages catégories générées.')

if __name__ == "__main__":
    main()
