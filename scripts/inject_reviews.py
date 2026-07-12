#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Injecte la Note MediaCritic sur les pages épisodes à partir de data/mc_reviews.json :
- un bloc visuel (note /10 + verdict) inséré avant la card « Ce que MediaCritic en a pensé »
- un JSON-LD schema.org/Review (reviewRating 0-10) inséré avant </head>

Idempotent : met à jour le bloc et le JSON-LD s'ils existent déjà.
Usage : python scripts/inject_reviews.py
"""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).parent.parent
REVIEWS = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
BASE = "https://www.mediacritic.fr"

def h(s):
    return html.escape(str(s), quote=True)

def fmt_note(n):
    return str(n).replace(".", ",").replace(",0", "")

def note_block(note, verdict):
    return (
        '<!-- mc-note-block -->\n'
        '  <div class="mc-note-block" style="display:flex;align-items:center;gap:22px;padding:22px 28px;'
        'border-radius:16px;background:linear-gradient(135deg,rgba(232,98,45,.12),rgba(245,166,35,.05));'
        'border:1px solid rgba(232,98,45,.35);margin-bottom:20px;">\n'
        f'    <div style="font-family:\'Syne\',sans-serif;font-size:2.6rem;font-weight:800;line-height:1;'
        'background:linear-gradient(90deg,#e8622d,#f5a623);-webkit-background-clip:text;'
        f'-webkit-text-fill-color:transparent;white-space:nowrap;">{fmt_note(note)}<span style="font-size:1.1rem;">/10</span></div>\n'
        '    <div>\n'
        '      <div style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        'color:var(--c-gold);margin-bottom:4px;">★ Note MediaCritic</div>\n'
        f'      <p style="color:var(--c-muted2);font-size:.9rem;line-height:1.6;">{h(verdict)}</p>\n'
        '    </div>\n'
        '  </div>\n'
        '  <!-- /mc-note-block -->'
    )

def review_ld(title, slug, note, verdict):
    data = {
        "@context": "https://schema.org",
        "@type": "Review",
        "itemReviewed": {"@type": "PodcastSeries", "name": title,
                         "url": f"{BASE}/fiches/{slug}.html"},
        "reviewRating": {"@type": "Rating", "ratingValue": note,
                         "bestRating": 10, "worstRating": 0},
        "author": {"@type": "Organization", "name": "MediaCritic", "url": BASE + "/"},
        "publisher": {"@type": "Organization", "name": "MediaCritic"},
        "reviewBody": verdict,
        "inLanguage": "fr",
    }
    return ('<script type="application/ld+json" data-mc-review>'
            + json.dumps(data, ensure_ascii=False) + "</script>")

updated = 0
for ep, r in sorted(REVIEWS.items(), key=lambda kv: int(kv[0])):
    path = ROOT / "episodes" / r["page"]
    if not path.exists():
        print(f"  ! page absente : {r['page']}")
        continue
    content = path.read_text(encoding="utf-8")

    # 1. Bloc visuel (remplace s'il existe, sinon insère avant la card verdict)
    block = note_block(r["note"], r["verdict"])
    if "<!-- mc-note-block -->" in content:
        content = re.sub(r"<!-- mc-note-block -->.*?<!-- /mc-note-block -->",
                         block, content, flags=re.DOTALL)
    else:
        content, n = re.subn(
            r'(<div class="card">\s*<h2>🔍 Ce que MediaCritic en a pensé</h2>)',
            block + r"\n\n  \1", content, count=1)
        if n == 0:
            print(f"  ! point d'injection introuvable : {r['page']}")
            continue

    # 2. JSON-LD Review (remplace s'il existe, sinon insère avant </head>)
    ld = review_ld(r["title"], r["slug"], r["note"], r["verdict"])
    if "data-mc-review" in content:
        content = re.sub(r'<script type="application/ld\+json" data-mc-review>.*?</script>',
                         ld, content, flags=re.DOTALL)
    else:
        content = content.replace("</head>", "  " + ld + "\n</head>", 1)

    path.write_text(content, encoding="utf-8")
    updated += 1
    print(f"  Ep{ep:>2} {r['page']} → note {r['note']}")

print(f"\n{updated}/{len(REVIEWS)} pages épisodes mises à jour.")
