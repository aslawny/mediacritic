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

# ─── Chemins ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data" / "content"
FICHES_DIR = ROOT / "fiches"
CATALOG    = ROOT / "data" / "catalog.json"
SITEMAP    = ROOT / "sitemap.xml"

FICHES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.mediacritic.fr"

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
@media(max-width:600px){.fiche-header{flex-direction:column}.fiche-cover{width:100%;height:200px}.container{padding:40px 18px 60px}}"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def h(text):
    """Escape HTML special characters."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def type_label(t):
    labels = {"podcast": "Podcast", "youtube": "Chaîne YouTube", "serie": "Série", "film": "Film"}
    return labels.get(t, t.capitalize() if t else "Média")


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
    desc_meta = description[:160].replace('"', "'")
    desc_full = description  # description complète pour la fiche

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

    # Bouton MediaCritic sur une ligne séparée en dessous des plateformes
    mc_action_html = ""
    if mediacritic:
        ep_slug_btn = mediacritic.get("episodeSlug", slug)
        mc_action_html = f'\n      <div class="actions" style="margin-top:8px"><a href="/episodes/{h(ep_slug_btn)}.html" class="btn btn-mc">📖 Analyse MediaCritic</a></div>'

    actions_html = "\n      ".join(platform_actions)

    # MC block
    mc_block = ""
    if mediacritic:
        ep_num = mediacritic.get("episodeNumber", "")
        ep_slug = mediacritic.get("episodeSlug", slug)
        mc_block = f"""
  <div class="mc-block">
  <h2>✦ L'avis MediaCritic — Épisode {ep_num}</h2>
  <p>Alex, Lolo et leurs invité·e·s ont analysé <strong>{h(title)}</strong> dans l'épisode&nbsp;{ep_num} de MediaCritic. Fond, forme, intentions — le verdict complet est disponible en écoute libre.</p>
  <div style="margin-top:16px"><a href="/episodes/{h(ep_slug)}.html" class="btn btn-mc">📖 Lire l'analyse complète</a></div>
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
        f'<a href="../catalogue.html?cat={h(cat)}" style="color:var(--c-orange);font-weight:600">{h(cat)}</a>'
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
        "author": {"@type": "Person", "name": author or "MediaCritic"},
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
  <script type="application/ld+json">{json.dumps(breadcrumb_schema, ensure_ascii=False)}</script>

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet" />
  <style>
{CSS_BLOCK}
</style>
</head>
<body>
<nav>
  <div class="nav-left">
    <a href="../" class="nav-back">← Accueil</a>
    <span class="nav-brand">MediaCritic</span>
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
      <div class="author">par {h(author or "MediaCritic")}</div>
      {rating_html}
      <div class="actions">{actions_html}</div>{mc_action_html}
    </div>
  </div>
{mc_block}
  <div class="card">
    <h2>À propos de {h(title)}</h2>
    <p>{h(desc_full).replace(chr(10), '<br>')}</p>{stats_html}{cats_html}
  </div>

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
            "tags":           d.get("tags", []),
            "image":          d.get("image"),
            "description":    (d.get("description") or "")[:200],
            "hasMediacritic": bool(d.get("mediacritic")),
            "mcEpisode":      d.get("mediacritic", {}).get("episodeNumber") if d.get("mediacritic") else None,
            "rating":         d.get("platforms", {}).get("apple", {}).get("rating"),
            "ratingCount":    d.get("platforms", {}).get("apple", {}).get("ratingCount"),
            "addedAt":        d.get("updatedAt", ""),
            "subscribers":    d.get("platforms", {}).get("youtube", {}).get("subscribers"),
        })
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  catalog.json → {len(catalog)} entrées")


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
            pass

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

    generated = 0
    skipped = 0
    updated = 0
    all_data = []
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

        all_data.append(data)
        html_path = FICHES_DIR / f"{slug}.html"
        processed_slugs.append(slug)

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
