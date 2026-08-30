#!/usr/bin/env python3
"""
MediaCritic — Génération des fiches HTML statiques
Usage: python scripts/generate_fiches.py  (depuis la racine du repo)
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

# ─── Chemins ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data" / "content"
FICHES_DIR = ROOT / "fiches"
CATALOG    = ROOT / "data" / "catalog.json"
SITEMAP    = ROOT / "sitemap.xml"

FICHES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.mediacritic.fr"

# ─── Pages catégories statiques (SEO) ──────────────────────────────────────────
# Liens des fiches → page catégorie dédiée quand elle existe, sinon fallback
# vers catalogue.html?cat= (qui est Disallow dans robots.txt).
# Tenir à jour quand on ajoute une page dans categories/.
CATEGORY_PAGES = {
    "histoire", "gaming", "tech", "sport", "cuisine-gastronomie",
    "true-crime", "sciences", "business", "cinema-series",
    "culture-societe", "musique", "humour", "voyage",
}
CATEGORY_ALIASES = {  # catégorie du catalogue → nom de la page
    "cuisine": "cuisine-gastronomie",
    "gastronomie": "cuisine-gastronomie",
    "true crime": "true-crime",
    "vulgarisation": "sciences",
    "entrepreneuriat": "business",
    "economie": "business",
    "cinema": "cinema-series",
    "series": "cinema-series",
    "culture": "culture-societe",
    "societe": "culture-societe",
    "comedie": "humour",
    "numerique": "tech",
    "arts": "culture-societe",
}

def category_href(cat):
    import urllib.parse
    page = CATEGORY_ALIASES.get(cat, cat)
    if page in CATEGORY_PAGES:
        return f"../categories/{page}.html"
    return f"../catalogue.html?cat={urllib.parse.quote(cat)}"

# ─── Blocklist ────────────────────────────────────────────────────────────────
def load_blocklist():
    bl_path = ROOT / "data" / "blocklist.json"
    if bl_path.exists():
        try:
            return set(json.load(open(bl_path, encoding="utf-8")))
        except Exception:
            pass
    return set()

BLOCKLIST = load_blocklist()

# Notes MediaCritic par numéro d'épisode (note /10 + verdict)
def load_mc_reviews():
    p = ROOT / "data" / "mc_reviews.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}

MC_REVIEWS = load_mc_reviews()

# ─── CSS bloc (extrait de braincast.html) ─────────────────────────────────────
CSS_BLOCK = """\
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--c-bg:#060b14;--c-bg2:#091220;--c-glass:rgba(255,255,255,.04);--c-border:rgba(255,255,255,.06);--c-border2:rgba(255,255,255,.10);--c-orange:#e8622d;--c-gold:#f5a623;--c-text:#f0e8d8;--c-muted:#7d93b0;--c-muted2:#a8bcd4}
body{font-family:'Inter',sans-serif;background:var(--c-bg);color:var(--c-text);line-height:1.7;min-height:100vh}
a{color:inherit;text-decoration:none}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(ellipse 80% 50% at 20% -10%,rgba(232,98,45,.10) 0%,transparent 60%),radial-gradient(ellipse 60% 40% at 80% 10%,rgba(245,166,35,.06) 0%,transparent 55%)}
*{position:relative;z-index:1}
nav{position:sticky;top:0;z-index:100;background:rgba(6,11,20,.92);border-bottom:1px solid var(--c-border);backdrop-filter:blur(20px);padding:0 32px;display:flex;align-items:center;justify-content:space-between;height:64px}
.nav-left{display:flex;align-items:center;gap:16px}
.nav-back{color:var(--c-muted);font-size:.875rem;font-weight:500;transition:color .2s}
.nav-back:hover{color:var(--c-orange)}
.nav-brand{font-family:'Syne',sans-serif;font-weight:800;font-size:1.05rem;background:linear-gradient(90deg,#e8622d,#f5a623);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-tag{font-size:.78rem;color:var(--c-muted);font-weight:500}
.container{max-width:800px;margin:0 auto;padding:60px 24px 80px}
.fiche-header{display:flex;gap:28px;align-items:flex-start;margin-bottom:40px}
.fiche-cover{width:140px;height:140px;flex-shrink:0;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.5)}
.fiche-cover img{width:100%;height:100%;object-fit:cover;display:block}
.fiche-cover-ph{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:800;font-family:'Syne',sans-serif;color:rgba(255,255,255,.55);background:linear-gradient(135deg,#1a2030,#0d1220)}
.fiche-meta{flex:1}
.breadcrumb{font-size:.75rem;color:var(--c-muted);margin-bottom:10px}
.breadcrumb a{color:var(--c-orange)}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;align-items:center}
.badge{display:inline-block;font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:3px 12px;border-radius:99px}
.badge-type{color:var(--c-muted2);background:var(--c-glass);border:1px solid var(--c-border2)}
.badge-mc{color:var(--c-gold);background:rgba(245,166,35,.12);border:1px solid rgba(245,166,35,.3)}
.badge-cat{color:var(--c-muted);background:var(--c-glass);border:1px solid var(--c-border);font-size:.68rem}
h1{font-family:'Syne',sans-serif;font-size:clamp(1.5rem,4vw,2.2rem);font-weight:800;line-height:1.18;margin-bottom:6px}
.author{font-size:.85rem;color:var(--c-muted2);margin-bottom:14px}
.rating-row{display:flex;align-items:center;gap:8px;margin-bottom:14px}
.stars{color:var(--c-gold);font-size:1rem}
.rating-num{font-weight:700}
.rating-count{font-size:.8rem;color:var(--c-muted)}
.actions{display:flex;gap:10px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:8px;padding:10px 20px;border-radius:99px;font-size:.85rem;font-weight:600;border:1px solid transparent;transition:transform .18s,opacity .18s}
.btn:hover{transform:translateY(-2px);opacity:.85}
.btn-spotify{background:rgba(29,185,84,.12);color:#4ade80;border-color:rgba(29,185,84,.3)}
.btn-youtube{background:rgba(255,0,0,.1);color:#ff6b6b;border-color:rgba(255,0,0,.25)}
.btn-apple{background:rgba(255,255,255,.06);color:var(--c-muted2);border-color:var(--c-border2)}
.btn-deezer{background:rgba(162,89,255,.10);color:#c084fc;border-color:rgba(162,89,255,.3)}
.btn-mc{background:linear-gradient(135deg,#e8622d,#f5a623);color:#fff;box-shadow:0 4px 16px rgba(232,98,45,.3)}
/* mc-partage */
.pt-card h2{margin-bottom:12px}
.pt-row{display:flex;gap:8px;flex-wrap:wrap}
.pt-btn{display:inline-block;padding:8px 15px;border-radius:9px;border:1px solid rgba(255,255,255,.10);font-size:.85rem;font-weight:600;text-decoration:none;cursor:pointer;font-family:inherit;line-height:1.4;transition:border-color .15s}
.pt-btn:hover{border-color:#e8622d}
.pt-x,.pt-copie{background:rgba(255,255,255,.05);color:#e8eaed}
.pt-li{background:rgba(10,102,194,.14);color:#6aa9e0}
.pt-fb{background:rgba(24,119,242,.12);color:#7ab0f5}
.pt-wa{background:rgba(37,211,102,.12);color:#5fd68f}
@media(max-width:520px){.pt-btn{padding:8px 12px;font-size:.8rem}}
.card{padding:28px 32px;border-radius:16px;background:var(--c-glass);border:1px solid var(--c-border);margin-bottom:20px}
.card h2{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--c-orange);margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--c-border)}
.card p{color:var(--c-muted2);font-size:.925rem;line-height:1.75}
.stats-row{display:flex;gap:20px;flex-wrap:wrap;margin-top:14px}
.stat-item{display:flex;flex-direction:column;gap:2px}
.stat-val{font-size:1.1rem;font-weight:700;color:var(--c-text)}
.stat-lbl{font-size:.72rem;color:var(--c-muted);text-transform:uppercase;letter-spacing:.08em}
.mc-block{border:1px solid rgba(232,98,45,.3);background:rgba(232,98,45,.04);border-radius:16px;padding:28px 32px;margin-bottom:20px}
.mc-block h2{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--c-orange);margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid rgba(232,98,45,.2)}
.mc-block p{color:var(--c-muted2);font-size:.925rem;line-height:1.75}
footer{text-align:center;padding:24px;border-top:1px solid var(--c-border);color:var(--c-muted);font-size:.8rem}
footer a{color:var(--c-muted);transition:color .2s}
footer a:hover{color:var(--c-orange)}
/* Maillage lateral : bloc « A decouvrir aussi ». Sobre volontairement — la
   fiche doit rester lisible, la grille sert de rebond, pas de vitrine. */
.sim-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}
.sim-item{display:flex;flex-direction:column;gap:6px;transition:transform .18s}
.sim-item:hover{transform:translateY(-3px)}
.sim-item:hover .sim-title{color:var(--c-orange)}
.sim-cover{position:relative;aspect-ratio:1;border-radius:10px;overflow:hidden;background:linear-gradient(135deg,#1a2030,#0d1220);display:flex;align-items:center;justify-content:center}
.sim-cover img{width:100%;height:100%;object-fit:cover;display:block}
.sim-ph{font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;color:rgba(255,255,255,.5)}
.sim-mc{position:absolute;top:5px;right:5px;font-size:.7rem;color:var(--c-gold);background:rgba(6,11,20,.82);border-radius:99px;padding:1px 5px;line-height:1.4}
.sim-title{font-size:.82rem;font-weight:600;line-height:1.3;transition:color .2s;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.sim-author{font-size:.72rem;color:var(--c-muted)}
/* Sous-notes et points forts / faibles d'une critique */
.crit-bloc{margin-top:18px;padding-top:16px;border-top:1px solid rgba(232,98,45,.2)}
.crit-list{list-style:none;display:flex;flex-direction:column;gap:9px;margin-bottom:16px}
.crit-list li{display:flex;align-items:center;gap:12px;font-size:.85rem}
.crit-nom{flex:0 0 40%;color:var(--c-muted2)}
.crit-jauge{flex:1;height:6px;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden}
.crit-jauge span{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#e8622d,#f5a623)}
.crit-note{flex:0 0 34px;text-align:right;font-weight:700;color:var(--c-text)}
.pts{margin-top:14px}
.pts h3{font-size:.78rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:7px}
.pts.pf h3{color:#4ade80}
.pts.pw h3{color:#f5a623}
.pts ul{list-style:none;display:flex;flex-direction:column;gap:5px}
.pts li{font-size:.875rem;color:var(--c-muted2);padding-left:16px;position:relative}
.pts li::before{content:'';position:absolute;left:0;top:.6em;width:6px;height:6px;border-radius:50%;background:currentColor;opacity:.5}
.pts.pf li::before{background:#4ade80}
.pts.pw li::before{background:#f5a623}
@media(max-width:520px){.crit-nom{flex:0 0 34%;font-size:.8rem}}
/* Derniers contenus publies */
.ep-list{list-style:none;margin-top:12px;display:flex;flex-direction:column;gap:8px}
.ep-list li{display:flex;gap:12px;align-items:baseline;font-size:.88rem;color:var(--c-muted2);padding-bottom:8px;border-bottom:1px solid var(--c-border)}
.ep-list li:last-child{border-bottom:0;padding-bottom:0}
.ep-date{flex:0 0 84px;font-size:.75rem;color:var(--c-muted);font-variant-numeric:tabular-nums}
@media(max-width:520px){
.sim-grid{grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:11px}
.ep-list li{flex-direction:column;gap:2px}
.ep-date{flex:none}
}
@media(max-width:600px){.fiche-header{flex-direction:column}.fiche-cover{width:100%;height:200px}.container{padding:40px 18px 60px}}"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def h(text):
    """Escape HTML special characters."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def type_label(t):
    labels = {"podcast": "Podcast", "youtube": "Chaîne YouTube", "serie": "Série", "film": "Film"}
    return labels.get(t, t.capitalize() if t else "Média")


def clean_author(author, title):
    """Retourne un nom d'auteur propre — remplace les emails par le titre du média."""
    if author and "@" in author:
        return title
    return author or "MediaCritic"


def schema_type(t):
    types = {"podcast": "PodcastSeries", "youtube": "WebPage"}
    return types.get(t, "CreativeWork")


def stars_html(rating):
    if not rating:
        return ""
    r = float(rating)
    full = int(r)
    half = 1 if (r - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


# ─── Maillage latéral ─────────────────────────────────────────────────────────
# 88 % des fiches n'étaient atteignables que par le sitemap ou le JS, et aucune
# ne pointait vers une autre : chaque page était un cul-de-sac, pour le visiteur
# comme pour le crawl. Cet index alimente le bloc « à découvrir aussi ».
INDEX_SIMILAIRES = {}
ANNEAU = {}


def construire_index(all_data):
    INDEX_SIMILAIRES.clear()
    for d in all_data:
        pf = d.get("platforms") or {}
        pop = (int((pf.get("apple") or {}).get("ratingCount") or 0)
               or int((pf.get("youtube") or {}).get("subscribers") or 0) // 1000)
        fiche = {"slug": d.get("slug"), "title": d.get("title", ""),
                 "image": d.get("image"), "type": d.get("type", "podcast"),
                 "auteur": d.get("author", ""), "pop": pop,
                 "mc": bool(d.get("mediacritic"))}
        for c in (d.get("categories") or [])[:3]:
            INDEX_SIMILAIRES.setdefault(c, []).append(fiche)
    for lst in INDEX_SIMILAIRES.values():
        # Les contenus analysés d'abord : ce sont nos pages les plus
        # qualitatives, et elles ramènent vers le podcast.
        lst.sort(key=lambda f: (not f["mc"], -f["pop"], f["title"].lower()))
    # Anneau alphabétique : les recommandations par popularité ramènent
    # toujours les mêmes fiches, laissant les autres orphelines (11 % → 16 %
    # d'atteignabilité seulement). En liant chaque fiche à ses deux voisines
    # alphabétiques, on ferme une chaîne qui parcourt toute la catégorie et
    # rend chaque page joignable par un lien HTML.
    ANNEAU.clear()
    for c, lst in INDEX_SIMILAIRES.items():
        ordonne = sorted(lst, key=lambda f: (f["title"].lower(), f["slug"]))
        for i, f in enumerate(ordonne):
            ANNEAU.setdefault(f["slug"], []).append(ordonne[(i + 1) % len(ordonne)])


def similaires(data, maxi=6):
    """Même catégorie, même type de préférence, les plus consultés d'abord.
    Jamais de recommandation inventée : uniquement des fiches existantes."""
    vus = {data.get("slug")}
    choix = []
    # Au plus 2 contenus analyses : au-dela, une categorie large comme
    # « culture » ne remontait QUE nos propres critiques, au detriment de la
    # pertinence. Deux suffisent a ramener vers le podcast.
    MAX_MC = 2
    nb_mc = 0
    for meme_type in (True, False):
        for c in (data.get("categories") or []):
            for f in INDEX_SIMILAIRES.get(c, []):
                if f["slug"] in vus:
                    continue
                if meme_type and f["type"] != data.get("type", "podcast"):
                    continue
                if f["mc"] and nb_mc >= MAX_MC:
                    continue
                vus.add(f["slug"])
                choix.append(f)
                nb_mc += f["mc"]
                if len(choix) >= maxi:
                    return choix
    return choix


def bloc_similaires(data):
    items = similaires(data)
    # Voisins de l'anneau : garantissent qu'aucune fiche ne reste orpheline.
    # A ajouter AVANT la construction des cartes, sinon ils ne sont pas rendus.
    deja = {f["slug"] for f in items} | {data.get("slug")}
    for v in ANNEAU.get(data.get("slug"), []):
        if v["slug"] not in deja:
            items.append(v)
            deja.add(v["slug"])
    if not items:
        return ""
    cartes = []
    for f in items:
        if f["image"]:
            vign = '<img src="%s" alt="%s" loading="lazy" />' % (h(f["image"]), h(f["title"]))
        else:
            ini = "".join(w[0].upper() for w in f["title"].split()[:2]) or "?"
            vign = '<span class="sim-ph">%s</span>' % h(ini)
        etoile = '<span class="sim-mc" title="Analysé par MediaCritic">★</span>' if f["mc"] else ""
        cartes.append(
            '<a class="sim-item" href="%s.html"><span class="sim-cover">%s%s</span>'
            '<span class="sim-title">%s</span><span class="sim-author">%s</span></a>'
            % (h(f["slug"]), vign, etoile, h(f["title"]), h(f["auteur"][:30])))
    cats = data.get("categories") or []
    lien = ""
    if cats:
        lien = ('<div style="margin-top:18px"><a class="btn btn-mc" href="%s">'
                'Tout voir en %s →</a></div>' % (category_href(cats[0]), h(cats[0])))
    return ('  <div class="card">    <h2>À découvrir aussi</h2>'
            '    <div class="sim-grid">%s</div>%s  </div>'
            % ("".join(cartes), lien))




def bloc_criteres(review):
    """Sous-notes et points forts / faibles d'une critique MediaCritic.

    Tout est OPTIONNEL : les 42 episodes publies avant l'introduction de ce
    modele n'ont qu'une note globale et un verdict. Rien ne s'affiche quand la
    donnee manque -- on ne fabrique pas un detail qu'on n'a pas."""
    criteres = review.get("criteres") or {}
    forts = review.get("points_forts") or []
    faibles = review.get("points_faibles") or []
    if not criteres and not forts and not faibles:
        return ""
    out = []
    if criteres:
        barres = ""
        for nom, val in criteres.items():
            pct = max(0, min(100, float(val) * 10))
            note = str(val).replace(".", ",").replace(",0", "")
            barres += ('<li><span class="crit-nom">%s</span>'
                       '<span class="crit-jauge"><span style="width:%.0f%%"></span></span>'
                       '<span class="crit-note">%s</span></li>' % (h(nom), pct, h(note)))
        out.append('<ul class="crit-list">%s</ul>' % barres)
    for titre, items, cls in (("Points forts", forts, "pf"),
                              ("Points faibles", faibles, "pw")):
        if items:
            li = "".join("<li>%s</li>" % h(x) for x in items)
            out.append('<div class="pts %s"><h3>%s</h3><ul>%s</ul></div>' % (cls, titre, li))
    return '<div class="crit-bloc">%s</div>' % "".join(out)


def bloc_episodes(data):
    """Derniers episodes, frequence et derniere activite. Rien n'est affiche
    si la donnee manque : certains flux ne l'exposent pas."""
    eps = data.get("episodes_recents") or []
    freq = data.get("frequence_jours")
    derniere = data.get("derniere_activite")
    if not eps and not freq and not derniere:
        return ""
    meta = []
    if freq is not None:
        if freq <= 2:
            meta.append("Publie quotidiennement")
        elif freq <= 9:
            meta.append("Publie chaque semaine environ")
        elif freq <= 20:
            meta.append("Publie tous les 15 jours environ")
        else:
            meta.append("Publie environ tous les %d jours" % freq)
    if derniere:
        try:
            j = date.fromisoformat(derniere)
            meta.append("dernier contenu le %s" % j.strftime("%d/%m/%Y"))
        except ValueError:
            pass
    lignes = "".join(
        '<li><span class="ep-date">%s</span>%s</li>'
        % (h(e.get("date") or ""), h(e.get("titre") or ""))
        for e in eps)
    liste = '<ul class="ep-list">%s</ul>' % lignes if lignes else ""
    intro = '<p>%s.</p>' % h(" — ".join(meta)) if meta else ""
    return ('  <div class="card"><h2>Derniers contenus publiés</h2>%s%s</div>'
            % (intro, liste))



# ── Partage social ───────────────────────────────────────────────────────────
# Aucun widget tiers : les boutons officiels de X, LinkedIn ou Facebook sont
# des traceurs, ils pesent plusieurs dizaines de Ko et la CSP du site les
# bloquerait de toute facon. Ici : quatre liens <a> et un bouton qui copie
# l'URL. Zero requete reseau, zero cookie, ~700 octets par page.
RESEAUX = (
    ("X", "https://twitter.com/intent/tweet?text={texte}&url={url}", "x"),
    ("LinkedIn", "https://www.linkedin.com/sharing/share-offsite/?url={url}", "li"),
    ("Facebook", "https://www.facebook.com/sharer/sharer.php?u={url}", "fb"),
    ("WhatsApp", "https://wa.me/?text={texte}%20{url}", "wa"),
)


def note_mc(data):
    """Note MediaCritic d'une fiche, ou None. Gere les DEUX formes du champ
    `mediacritic` qui coexistent dans les donnees : 31 fiches en
    `episodeNumber`, 14 en `ep`. Tant que la normalisation n'est pas faite,
    lire une seule des deux formes perdrait un tiers des notes."""
    mc = data.get("mediacritic")
    if not isinstance(mc, dict):
        return None
    ep = mc.get("episodeNumber", mc.get("ep"))
    if ep is None:
        return None
    return (MC_REVIEWS.get(str(ep)) or {}).get("note")


def bloc_partage(data):
    """Rangee de partage. Le texte pre-rempli porte la note quand elle existe :
    « Floodcast : 8,5/10 sur MediaCritic » se partage, « Floodcast » non."""
    titre = data.get("title") or data["slug"]
    url = quote(f"{BASE_URL}/fiches/{data['slug']}.html", safe="")
    n = note_mc(data)
    if n is not None:
        texte = f"{titre} : {str(n).replace('.', ',')}/10 sur MediaCritic"
    else:
        texte = f"{titre} — dans l'annuaire MediaCritic"
    texte = quote(texte, safe="")

    liens = "".join(
        '<a class="pt-btn pt-%s" href="%s" target="_blank" '
        'rel="noopener noreferrer nofollow" aria-label="Partager sur %s">%s</a>'
        % (cls, gabarit.format(texte=texte, url=url), nom, nom)
        for nom, gabarit, cls in RESEAUX)

    # onclick inline plutot qu'un <script> : une balise de moins sur 8 300 pages.
    copie = ('<button type="button" class="pt-btn pt-copie" '
             "onclick=\"navigator.clipboard.writeText(location.href).then("
             "()=&gt;{this.textContent='Lien copié';"
             "setTimeout(()=&gt;{this.textContent='Copier le lien'},2000)},()=&gt;{this.textContent='Copie impossible'})\">"
             "Copier le lien</button>")

    return ('  <div class="card pt-card"><h2>🔗 Partager cette fiche</h2>'
            '<div class="pt-row">' + liens + copie + "</div></div>")

def render_fiche(data):
    slug = data["slug"]
    title = data.get("title", slug)
    author = data.get("author", "")
    content_type = data.get("type", "podcast")
    categories = data.get("categories", [])
    description = data.get("description") or ""
    image = data.get("image")
    platforms = data.get("platforms", {})
    mediacritic = data.get("mediacritic")

    t_label = type_label(content_type)
    author_display = clean_author(author, title)

    # Description : fallback si vide pour éviter content=""
    if description.strip():
        desc_meta = description[:160].replace('"', "'")
    else:
        desc_meta = f"{title} — {t_label} francophone référencé sur MediaCritic."[:160]
    desc_full = description  # description complète pour la fiche (peut rester vide)

    # Cover block
    if image:
        cover_html = f'<img src="{h(image)}" alt="{h(title)}" loading="lazy" />'
    else:
        initials = "".join(w[0].upper() for w in title.split()[:2]) or title[0].upper()
        cover_html = f'<div class="fiche-cover-ph">{h(initials)}</div>'

    # Badges
    badges = [f'<span class="badge badge-type">{h(t_label)}</span>']
    if mediacritic:
        badges.append('<span class="badge badge-mc">✦ Analysé par MediaCritic</span>')
    for cat in categories:
        badges.append(f'<span class="badge badge-cat">{h(cat)}</span>')
    badges_html = " ".join(badges)

    # Rating
    apple = platforms.get("apple", {})
    rating = apple.get("rating")
    rating_count = apple.get("ratingCount")
    rating_html = ""
    if rating:
        rating_html = (
            f'<div class="rating-row">'
            f'<span class="stars">{stars_html(rating)}</span>'
            f'<span class="rating-num">{float(rating):.1f}</span>'
            + (f'<span class="rating-count">({rating_count:,} notes)</span>' if rating_count else "")
            + "</div>"
        )

    # Action buttons — plateformes d'abord, MediaCritic en dessous
    import urllib.parse
    platform_actions = []
    if platforms.get("youtube", {}).get("url"):
        platform_actions.append(f'<a href="{h(platforms["youtube"]["url"])}" target="_blank" rel="noopener" class="btn btn-youtube">▶ YouTube</a>')
    if content_type == "podcast":
        # Apple Podcasts
        if platforms.get("apple", {}).get("url"):
            platform_actions.append(f'<a href="{h(platforms["apple"]["url"])}" target="_blank" rel="noopener" class="btn btn-apple">🎵 Apple Podcasts</a>')
        # Spotify : URL exacte si connue, sinon lien de recherche
        spotify_url = platforms.get("spotify", {}).get("url") or \
            f'https://open.spotify.com/search/{urllib.parse.quote(title)}'
        platform_actions.append(f'<a href="{h(spotify_url)}" target="_blank" rel="noopener" class="btn btn-spotify">🎧 Spotify</a>')
        # Deezer : URL exacte si connue, sinon lien de recherche
        deezer_url = platforms.get("deezer", {}).get("url") or \
            f'https://www.deezer.com/search/{urllib.parse.quote(title)}'
        platform_actions.append(f'<a href="{h(deezer_url)}" target="_blank" rel="noopener" class="btn btn-deezer">🎵 Deezer</a>')

    actions_html = "\n      ".join(platform_actions)

    # MC block
    mc_block = ""
    mc_review_ld = ""
    if mediacritic:
        ep_num = mediacritic.get("episodeNumber") or mediacritic.get("ep") or ""
        # URL de l'analyse : supporte analyseUrl/url (absolue) ou episodeSlug
        analyse_url = mediacritic.get("analyseUrl") or mediacritic.get("url")
        if analyse_url:
            href = analyse_url.replace("https://www.mediacritic.fr", "")
        else:
            href = f"/episodes/{mediacritic.get('episodeSlug', slug)}.html"
        # Note MediaCritic (data/mc_reviews.json, clé = numéro d'épisode)
        review = MC_REVIEWS.get(str(ep_num), {})
        note_html = ""
        if review.get("note") is not None:
            note_str = str(review["note"]).replace(".", ",").replace(",0", "")
            note_html = (
                '\n  <div style="display:flex;align-items:center;gap:18px;margin-bottom:14px;">'
                f'<div style="font-family:\'Syne\',sans-serif;font-size:2.2rem;font-weight:800;line-height:1;'
                'background:linear-gradient(90deg,#e8622d,#f5a623);-webkit-background-clip:text;'
                f'-webkit-text-fill-color:transparent;white-space:nowrap;">{note_str}<span style="font-size:1rem;">/10</span></div>'
                f'<p style="color:var(--c-muted2);font-size:.9rem;line-height:1.6;font-style:italic;">{h(review.get("verdict",""))}</p>'
                "</div>"
                + bloc_criteres(review)
            )
            review_data = {
                "@context": "https://schema.org",
                "@type": "Review",
                "itemReviewed": {"@type": "PodcastSeries", "name": title,
                                 "url": f"{BASE_URL}/fiches/{slug}.html"},
                "reviewRating": {"@type": "Rating", "ratingValue": review["note"],
                                 "bestRating": 10, "worstRating": 0},
                "author": {"@type": "Organization", "name": "MediaCritic", "url": BASE_URL + "/"},
                "publisher": {"@type": "Organization", "name": "MediaCritic"},
                "reviewBody": review.get("verdict", ""),
                "inLanguage": "fr",
            }
            # positiveNotes / negativeNotes : types prevus par schema.org pour
            # detailler un avis. Ajoutes seulement s'ils existent reellement.
            for cle, champ in (("points_forts", "positiveNotes"),
                               ("points_faibles", "negativeNotes")):
                if review.get(cle):
                    review_data[champ] = {
                        "@type": "ItemList",
                        "itemListElement": [
                            {"@type": "ListItem", "position": i + 1, "name": x}
                            for i, x in enumerate(review[cle])],
                    }
            mc_review_ld = ('\n  <script type="application/ld+json">'
                            + json.dumps(review_data, ensure_ascii=False) + "</script>")
        mc_block = f"""
  <div class="mc-block">
  <h2>✦ L'avis MediaCritic — Épisode {ep_num}</h2>{note_html}
  <p>Alex, Lolo et leurs invité·e·s ont analysé <strong>{h(title)}</strong> dans l'épisode&nbsp;{ep_num} de MediaCritic. Fond, forme, intentions — le verdict complet est disponible en écoute libre.</p>
  <div style="margin-top:16px"><a href="{h(href)}" class="btn btn-mc">📖 Lire l'analyse complète</a></div>
</div>
"""

    # Stats row
    stats_items = []
    if platforms.get("apple", {}).get("episodeCount"):
        stats_items.append(
            f'<div class="stat-item"><span class="stat-val">{platforms["apple"]["episodeCount"]}</span>'
            f'<span class="stat-lbl">épisodes</span></div>'
        )
    if platforms.get("youtube", {}).get("videoCount"):
        stats_items.append(
            f'<div class="stat-item"><span class="stat-val">{platforms["youtube"]["videoCount"]}</span>'
            f'<span class="stat-lbl">vidéos</span></div>'
        )
    if rating_count:
        stats_items.append(
            f'<div class="stat-item"><span class="stat-val">{rating_count:,}</span>'
            f'<span class="stat-lbl">notes</span></div>'
        )
    stats_html = ""
    if stats_items:
        stats_html = '\n    <div class="stats-row">' + "".join(stats_items) + "</div>"

    # Categories links
    cat_links = " · ".join(
        f'<a href="{category_href(cat)}" style="color:var(--c-orange);font-weight:600">{h(cat)}</a>'
        for cat in categories
    )
    cats_html = f'\n    <p style="margin-top:14px;font-size:.85rem;color:var(--c-muted)">Catégories : {cat_links}</p>' if cat_links else ""

    # JSON-LD
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type(content_type),
        "name": title,
        "description": desc_meta,
        "url": f"{BASE_URL}/fiches/{slug}.html",
        "image": image or f"{BASE_URL}/assets/banner.png",
        "inLanguage": "fr",
        "author": {"@type": "Person", "name": author_display},
    }
    # Note agregee de la plateforme. Condition posee par Google : la note doit
    # etre VISIBLE sur la page -- elle l'est, dans le bloc .rating-row.
    # C'est la note APPLE du podcast, pas celle de MediaCritic : la notre est
    # portee separement par le noeud Review, avec MediaCritic comme auteur.
    # Seuil de 3 avis : en dessous, une moyenne n'a aucune valeur statistique
    # et Google considere ces balisages comme trompeurs.
    _apple = platforms.get("apple") or {}
    _note, _nb = _apple.get("rating"), _apple.get("ratingCount")
    if _note and _nb and int(_nb) >= 3:
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": round(float(_note), 1),
            "ratingCount": int(_nb),
            "bestRating": 5,
            "worstRating": 1,
        }
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "Catalogue", "item": f"{BASE_URL}/catalogue.html"},
            {"@type": "ListItem", "position": 3, "name": title, "item": f"{BASE_URL}/fiches/{slug}.html"},
        ],
    }

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{h(title)} — {h(t_label)} | MediaCritic</title>
  <meta name="description" content="{h(desc_meta)}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{BASE_URL}/fiches/{slug}.html" />
  <link rel="icon" href="../assets/logo.png" type="image/png" />

  <meta property="og:type" content="website" />
  <meta property="og:url" content="{BASE_URL}/fiches/{slug}.html" />
  <meta property="og:title" content="{h(title)} — {h(t_label)} | MediaCritic" />
  <meta property="og:description" content="{h(desc_meta)}" />
  <meta property="og:image" content="{h(image) if image else BASE_URL + '/assets/banner.png'}" />
  <meta property="og:site_name" content="MediaCritic" />
  <meta property="og:locale" content="fr_FR" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{h(title)} — {h(t_label)} | MediaCritic" />
  <meta name="twitter:description" content="{h(desc_meta)}" />
  <meta name="twitter:image" content="{h(image) if image else BASE_URL + '/assets/banner.png'}" />

  <script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(breadcrumb_schema, ensure_ascii=False)}</script>{mc_review_ld}

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../assets/fiche.css" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-3W2VTTEWG8"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-3W2VTTEWG8');</script>
</head>
<body>
<nav>
  <div class="nav-left">
    <a href="../" class="nav-back">← Accueil</a>
    <span class="nav-brand">MediaCritic</span>
    <a href="../catalogue.html" class="nav-back">Annuaire</a>
    <a href="../classement.html" class="nav-back">Classement</a>
    <a href="../comparer.html" class="nav-back">Comparateur</a>
    <a href="../palmares.html" class="nav-back" style="color:var(--c-gold)">🏆 Palmarès</a>
  </div>
  <span class="nav-tag">{h(t_label)}</span>
</nav>

<div class="container">
  <div class="fiche-header">
    <div class="fiche-cover">{cover_html}</div>
    <div class="fiche-meta">
      <nav class="breadcrumb" aria-label="Fil d'Ariane">
        <a href="../">MediaCritic</a> ›
        <a href="../catalogue.html">Catalogue</a> ›
        {h(title)}
      </nav>
      <div class="badges">{badges_html}</div>
      <h1>{h(title)}</h1>
      <div class="author">par {h(author_display)}</div>
      {rating_html}
      <div class="actions">{actions_html}</div>
    </div>
  </div>
{mc_block}
  <div class="card">
    <h2>À propos de {h(title)}</h2>
    <p>{h(desc_full).replace(chr(10), '<br>')}</p>{stats_html}{cats_html}
  </div>

{bloc_episodes(data)}
{bloc_similaires(data)}
{bloc_partage(data)}
  <div class="card">
    <h2>📻 MediaCritic, c'est quoi ?</h2>
    <p>MediaCritic est le podcast francophone indépendant qui analyse et critique des podcasts, émissions et chaînes YouTube. Chaque semaine, Alex et Lolo décortiquent un média avec méthode, passion et humour.</p>
    <div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap">
      <a href="../catalogue.html" class="btn btn-mc">← Retour au catalogue</a>
    </div>
  </div>
</div>

<footer>
  <p>© {date.today().year} <a href="../">MediaCritic</a> — <a href="../mentions-legales.html">Mentions légales</a> — <a href="mailto:mediacriticinc@gmail.com">mediacriticinc@gmail.com</a></p>
</footer>
</body>
</html>"""
    return html


def needs_update(json_path, html_path):
    """Return True if HTML doesn't exist or JSON is newer than HTML."""
    if os.environ.get("MC_FORCE_REGEN") == "1":
        return True
    if not html_path.exists():
        return True
    json_mtime = json_path.stat().st_mtime
    html_mtime = html_path.stat().st_mtime
    return json_mtime > html_mtime


def update_catalog(all_data):
    catalog = []
    for d in sorted(all_data, key=lambda x: x.get("slug", "")):
        catalog.append({
            "slug":           d.get("slug"),
            "title":          d.get("title"),
            "author":         d.get("author", ""),
            "type":           d.get("type"),
            "categories":     d.get("categories", []),
            "image":          d.get("image"),
            # « tags » retire du catalogue : duplique « categories » et n'est
            # lu par AUCUN consommateur. Description tronquee a 80 caracteres :
            # elle ne sert qu'a la recherche Fuse (poids 0,1) et n'est jamais
            # affichee. Mesure sur 11 requetes : premier resultat identique,
            # recouvrement du top 10 de 9 a 10 sur 10.
            # Gain : 5,22 Mo -> 4,21 Mo (-19 %) sur la page d'accueil.
            "description":    (d.get("description") or "")[:80],
            "hasMediacritic": bool(d.get("mediacritic")),
            "mcEpisode":      (d.get("mediacritic") or {}).get("episodeNumber") or (d.get("mediacritic") or {}).get("ep"),
            "mcNote":         MC_REVIEWS.get(str((d.get("mediacritic") or {}).get("episodeNumber") or (d.get("mediacritic") or {}).get("ep")), {}).get("note"),
            "rating":         d.get("platforms", {}).get("apple", {}).get("rating"),
            "ratingCount":    d.get("platforms", {}).get("apple", {}).get("ratingCount"),
            "addedAt":        d.get("updatedAt", ""),
            "subscribers":    d.get("platforms", {}).get("youtube", {}).get("subscribers"),
        })
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  catalog.json → {len(catalog)} entrées")

    # catalog-lite.json : sous-ensemble prioritaire chargé en premier par la
    # home (perf mobile). Contenus MC d'abord, puis les mieux notés/suivis.
    mc_items = [c for c in catalog if c["hasMediacritic"]]
    others = sorted(
        (c for c in catalog if not c["hasMediacritic"]),
        key=lambda c: (c.get("rating") or 0, c.get("subscribers") or 0),
        reverse=True,
    )
    lite = mc_items + others[: max(0, 300 - len(mc_items))]
    with open(CATALOG.with_name("catalog-lite.json"), "w", encoding="utf-8") as f:
        json.dump(lite, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  catalog-lite.json → {len(lite)} entrées")
    update_counters(len(catalog))


def update_counters(total):
    """Synchronise les compteurs du catalogue affichés sur index.html et
    catalogue.html (meta, OG, Twitter, JSON-LD, bloc statique). Arrondi à la
    centaine inférieure pour rester vrai entre deux régénérations."""
    rounded = (total // 100) * 100
    disp = f"{rounded:,}".replace(",", " ")          # 9 400
    for name in ("index.html", "catalogue.html"):
        path = ROOT / name
        if not path.exists():
            continue
        txt = orig = path.read_text(encoding="utf-8")
        # « 7 400+ » / « 7 400 + » sous toutes leurs formes
        txt = re.sub(r"\d[\d   ]*\d\s*\+(?=\s*(?:podcasts|contenus))",
                     disp + "+", txt)
        # « parmi 7 400+ », « Découvrez 7 400+ »
        # (une balise peut s'intercaler : « Plus de <strong>1 360 contenus</strong> »)
        txt = re.sub(r"(parmi|Découvrez|Plus de|plus de)(\s+(?:<[^>]+>)?\s*)\d[\d\s\u00a0\u202f]*\d(\s*\+)?",
                     lambda m: f"{m.group(1)}{m.group(2)}{disp}" + ("+" if m.group(3) else ""), txt)
        # JSON-LD
        txt = re.sub(r'("numberOfItems"\s*:\s*)\d+', r"\g<1>" + str(rounded), txt)
        # valeur initiale du compteur héros (le JS la recalcule ensuite)
        txt = re.sub(r'(<div class="num" id="stat-total">)[^<]*(</div>)',
                     r"\g<1>" + disp + "+" + r"\g<2>", txt)
        if txt != orig:
            path.write_text(txt, encoding="utf-8")
            print(f"  {name} → compteurs synchronisés ({disp}+)")


def update_sitemap(slugs):
    today_str = date.today().isoformat()
    existing_urls = set()

    if SITEMAP.exists():
        try:
            tree = ET.parse(SITEMAP)
            root = tree.getroot()
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for url_el in root.findall("sm:url", ns):
                loc_el = url_el.find("sm:loc", ns)
                if loc_el is not None:
                    existing_urls.add(loc_el.text)
        except ET.ParseError:
            # Sitemap malformé (ex. marqueurs de conflit git) : on récupère
            # quand même les <loc> via regex pour ne PAS tout ré-ajouter en double.
            import re as _re
            raw = SITEMAP.read_text(encoding="utf-8")
            existing_urls.update(_re.findall(r"<loc>([^<]+)</loc>", raw))

    # Purge des URLs devenues mortes. Ce generateur n'ajoutait jamais que des
    # URLs : les fiches supprimees (blocklist, purge linguistique) laissaient
    # leur <loc> derriere elles, et Google recoltait des 404. Toute URL locale
    # dont le fichier n'existe plus est retiree.
    if SITEMAP.exists():
        raw = SITEMAP.read_text(encoding="utf-8")
        gardees, retirees = [], 0
        for ligne in raw.splitlines(keepends=True):
            m = re.search(r"<loc>" + re.escape(BASE_URL) + r"/([^<]*)</loc>", ligne)
            if m and m.group(1) and not (ROOT / m.group(1)).exists():
                retirees += 1
                existing_urls.discard(f"{BASE_URL}/{m.group(1)}")
                continue
            gardees.append(ligne)
        if retirees:
            SITEMAP.write_text("".join(gardees), encoding="utf-8")
            print(f"  sitemap.xml → {retirees} URL(s) morte(s) retirée(s)")

    new_urls = []
    for slug in slugs:
        fiche_url = f"{BASE_URL}/fiches/{slug}.html"
        if fiche_url not in existing_urls:
            new_urls.append(fiche_url)

    if not new_urls:
        return

    # Append new URLs to sitemap
    if SITEMAP.exists():
        content = SITEMAP.read_text(encoding="utf-8")
        # Insert before </urlset>
        insertions = ""
        for url in new_urls:
            insertions += f'  <url><loc>{url}</loc><lastmod>{today_str}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>\n'
        content = content.replace("</urlset>", insertions + "</urlset>")
        SITEMAP.write_text(content, encoding="utf-8")
    else:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>\n',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n']
        for url in new_urls:
            lines.append(f'  <url><loc>{url}</loc><lastmod>{today_str}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>\n')
        lines.append("</urlset>\n")
        SITEMAP.write_text("".join(lines), encoding="utf-8")

    print(f"  sitemap.xml → {len(new_urls)} nouvelle(s) URL(s) ajoutée(s)")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        print("Aucun fichier JSON trouvé dans data/content/")
        return

    # CSS partagé des fiches (externe : mis en cache par le navigateur,
    # au lieu d'être dupliqué inline dans chaque fiche)
    css_path = ROOT / "assets" / "fiche.css"
    if not css_path.exists() or css_path.read_text(encoding="utf-8") != CSS_BLOCK:
        css_path.write_text(CSS_BLOCK, encoding="utf-8")
        print("  assets/fiche.css mis à jour")

    generated = 0
    skipped = 0
    updated = 0
    all_data = []
    a_rendre = []
    processed_slugs = []

    for json_path in json_files:
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠ Erreur lecture {json_path.name}: {e}")
            continue

        slug = data.get("slug")
        if not slug:
            continue

        # Slug blackliste : supprimer le JSON et ignorer
        if slug in BLOCKLIST:
            json_path.unlink(missing_ok=True)
            fiche = FICHES_DIR / f"{slug}.html"
            fiche.unlink(missing_ok=True)
            continue

        all_data.append(data)
        processed_slugs.append(slug)
        a_rendre.append((json_path, data))

    # Le bloc « similaires » a besoin de TOUT le corpus : impossible de rendre
    # une fiche avant d'avoir lu les autres. D'ou ces deux passes.
    construire_index(all_data)
    for json_path, data in a_rendre:
        html_path = FICHES_DIR / f"{data['slug']}.html"
        if not needs_update(json_path, html_path):
            skipped += 1
            continue
        html = render_fiche(data)
        existed = html_path.exists()
        html_path.write_text(html, encoding="utf-8")
        if existed:
            updated += 1
        else:
            generated += 1

    print(f"Generated: {generated}, Skipped: {skipped}, Updated: {updated}")

    # Update catalog.json
    update_catalog(all_data)

    # Update sitemap.xml
    update_sitemap(processed_slugs)

    print("\n✅ Terminé.")


if __name__ == "__main__":
    main()
