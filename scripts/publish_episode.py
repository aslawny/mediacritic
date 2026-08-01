#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publication automatisée d'un épisode MediaCritic.

Prend un manifest JSON (voir manifests/) décrivant l'épisode et exécute tout
le rituel hebdomadaire :
  1. Génère la page épisode depuis templates/episode.html
  2. Ajoute la note à data/mc_reviews.json + injecte note/Review JSON-LD
     (inject_reviews.py) sur la nouvelle page
  3. Crée ou met à jour data/content/{slug}.json (champ mediacritic)
  4. index.html : MC_EP, compteurs N-1→N, liste statique SEO
  5. Épisode précédent : retire le badge "Nouveau", ajoute le lien "Suivant"
  6. qui-sommes-nous.html : ajoute l'épisode à la ligne de l'invité (si connu)
  7. sitemap.xml : nouvelle URL épisode
  8. Régénère fiches/catalogue (generate_fiches) et palmares
  9. Valide (JSON-LD, doublons sitemap, compteurs)
 10. Commit git ; --staging pousse une branche de sauvegarde ;
     --push publie sur gh-pages (avec résolution des conflits du bot)

Usage :
  python scripts/publish_episode.py manifests/ep37.json            # prépare + commit local
  python scripts/publish_episode.py manifests/ep37.json --staging  # + branche epN-staging
  python scripts/publish_episode.py manifests/ep37.json --push     # publie sur gh-pages

Aucun secret manipulé : l'authentification git passe par le credential
manager du système.
"""
import argparse, json, re, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
SHOW_SPOTIFY = "https://open.spotify.com/show/5JuffYLQq1q6l7Vh2zvkrV"

def run(cmd, check=True, capture=False):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=capture, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise SystemExit(f"ÉCHEC: {' '.join(cmd)}\n{(r.stderr or '') if capture else ''}")
    return r

def die(msg):
    raise SystemExit(f"✗ {msg}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--staging", action="store_true", help="pousse HEAD sur epN-staging")
    ap.add_argument("--push", action="store_true", help="publie sur gh-pages")
    args = ap.parse_args()

    m = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    ep, slug, page, title = m["ep"], m["slug"], m["page"], m["title"]
    reviews_path = ROOT / "data" / "mc_reviews.json"
    reviews = json.loads(reviews_path.read_text(encoding="utf-8"))

    if str(ep) in reviews and (ROOT / "episodes" / page).exists():
        print(f"! L'épisode {ep} existe déjà — relance idempotente.")
    prev_ep = max(int(k) for k in reviews if int(k) < ep)
    prev = reviews[str(prev_ep)]
    print(f"Épisode {ep} : {title} (précédent : {prev_ep} — {prev['title']})")

    # ── 1. Page épisode ──────────────────────────────────────────────────────
    tpl = (ROOT / "templates" / "episode.html").read_text(encoding="utf-8")
    authors_ld = ", ".join('{"@type":"Person","name":"%s"}' % a for a in m["authors"])
    buttons = "\n        ".join(
        f'<a href="{b["href"]}" target="_blank" rel="noopener noreferrer" class="ep-btn ep-btn-podcast"'
        + (f' style="{b["style"]}"' if b.get("style") else "") + f'>{b["label"]}</a>'
        for b in m["buttons"])

    # Liens d'écoute de NOTRE épisode. Renseignés dans le manifest (bloc
    # "listen") le jour de la publication, une fois l'épisode en ligne sur les
    # plateformes. Tant qu'ils manquent : bouton générique vers l'émission.
    listen = m.get("listen") or {}
    listen_specs = [
        ("spotify", "🎧 Écouter sur Spotify", 'class="ep-btn ep-btn-episode"'),
        ("apple", "🎵 Apple Podcasts",
         'class="ep-btn" style="background:rgba(255,255,255,.06);color:var(--c-muted2);border-color:var(--c-border2);"'),
        ("deezer", "🎵 Deezer",
         'class="ep-btn" style="background:rgba(162,89,255,.10);color:#c084fc;border-color:rgba(162,89,255,.3);"'),
        ("youtube", "▶ YouTube",
         'class="ep-btn" style="background:rgba(255,0,0,.10);color:#ff6b6b;border-color:rgba(255,0,0,.25);"'),
    ]
    if any(listen.get(k) for k, _, _ in listen_specs):
        listen_buttons = "\n        ".join(
            f'<a href="{listen[k]}" target="_blank" rel="noopener noreferrer" {attrs}>{label}</a>'
            for k, label, attrs in listen_specs if listen.get(k))
    else:
        listen_buttons = (f'<a href="{SHOW_SPOTIFY}" target="_blank" rel="noopener noreferrer" '
                          f'class="ep-btn ep-btn-episode">🎧 Écouter notre épisode</a>')
        print("  ! liens d'écoute absents du manifest → bouton générique (à compléter au go)")
    content_cards = Path(m["content_file"]).read_text(encoding="utf-8")
    subs = {
        "__EP__": str(ep), "__TITLE__": title, "__TAGLINE__": m["tagline"],
        "__META_DESC__": m["meta_desc"], "__PAGE__": page, "__COVER__": m["cover"],
        "__INITIALS__": m["initials"], "__TYPE_LINE__": m["type_line"],
        "__HOSTS_LINE__": m["hosts_line"], "__AUTHORS_LD__": authors_ld,
        "__BUTTONS__": buttons, "__CONTENT_CARDS__": content_cards,
        "__LISTEN_BUTTONS__": listen_buttons,
        "__EPISODE_URL__": listen.get("spotify") or SHOW_SPOTIFY,
        "__PREV_EP__": str(prev_ep), "__PREV_TITLE__": prev["title"],
        "__PREV_PAGE__": prev["page"],
    }
    out = tpl
    for k, v in subs.items():
        out = out.replace(k, v)
    if "__" in re.sub(r"<!--.*?-->", "", out):
        leftover = sorted(set(re.findall(r"__[A-Z_]+__", out)))
        die(f"placeholders non remplacés : {leftover}")
    (ROOT / "episodes" / page).write_text(out, encoding="utf-8")
    print(f"  ✓ episodes/{page}")

    # ── 2. Note + injection ─────────────────────────────────────────────────
    reviews[str(ep)] = {"slug": slug, "page": page, "title": title,
                        "note": m["note"], "verdict": m["verdict"]}
    reviews_path.write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
    run([sys.executable, "scripts/inject_reviews.py"])
    print(f"  ✓ note {m['note']}/10 injectée")

    # ── 3. data/content ─────────────────────────────────────────────────────
    cpath = ROOT / "data" / "content" / f"{slug}.json"
    if cpath.exists():
        cdata = json.loads(cpath.read_text(encoding="utf-8"))
    elif "content" in m:
        cdata = m["content"]
        cdata.setdefault("slug", slug)
        cdata.setdefault("addedAt", date.today().isoformat())
    else:
        die(f"data/content/{slug}.json absent et pas de bloc 'content' dans le manifest")
    cdata["mediacritic"] = {"ep": ep, "url": f"{BASE}/episodes/{page}"}
    cdata["updatedAt"] = date.today().isoformat()
    cpath.write_text(json.dumps(cdata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ data/content/{slug}.json")

    # ── 4. index.html ───────────────────────────────────────────────────────
    idx_path = ROOT / "index.html"
    idx = idx_path.read_text(encoding="utf-8")
    if f'"{slug}":{{ep:{ep}' not in idx:
        pos = idx.find("const MC_EP")
        end = idx.find("\n  };", pos)
        if pos < 0 or end < 0:
            die("bloc MC_EP introuvable dans index.html")
        entry = f'    "{slug}":{{ep:{ep},analyse:"episodes/{page}",img:"{m["cover"]}"}}'
        idx = idx[:end] + ",\n" + entry + idx[end:]
    for old, new in ((f'<div class="num">{prev_ep}</div>', f'<div class="num">{ep}</div>'),
                     (f'Saison 1 · {prev_ep} épisodes', f'Saison 1 · {ep} épisodes')):
        if old in idx:
            idx = idx.replace(old, new)
        elif new not in idx:
            die(f"compteur introuvable : {old}")
    li = (f'    <li><a href="episodes/{page}" style="color:var(--c-muted2);'
          f'font-size:.88rem;">Ép. {ep} — {title}</a></li>')
    anchor = f'<li><a href="episodes/{prev["page"]}"'
    if f'episodes/{page}"' not in idx.split("const MC_EP")[0] or li not in idx:
        if anchor not in idx:
            die("liste statique : ancre épisode précédent introuvable")
        idx = idx.replace("    " + anchor, li + "\n    " + anchor, 1)
    idx_path.write_text(idx, encoding="utf-8")
    print(f"  ✓ index.html (MC_EP + compteurs {prev_ep}→{ep} + liste)")

    # ── 5. Épisode précédent ────────────────────────────────────────────────
    ppath = ROOT / "episodes" / prev["page"]
    phtml = ppath.read_text(encoding="utf-8")
    phtml = phtml.replace('<span class="ep-new-badge">✨ Nouveau</span>', "")
    if "nav-ep-btn next" not in phtml:
        nxt = (f'    <a href="{page}" class="nav-ep-btn next"><span>Suivant →</span>'
               f'Ép. {ep} — {title}</a>\n  </nav>')
        phtml = re.sub(r'(\s*)</nav>\n</div>\n\n<footer>', "\n" + nxt + "\n</div>\n\n<footer>",
                       phtml, count=1)
    ppath.write_text(phtml, encoding="utf-8")
    print(f"  ✓ {prev['page']} (badge retiré, lien Suivant)")

    # ── 6. Invité ───────────────────────────────────────────────────────────
    if m.get("guest"):
        qpath = ROOT / "qui-sommes-nous.html"
        q = qpath.read_text(encoding="utf-8")
        pat = re.compile(
            r'(<div class="guest-name">' + re.escape(m["guest"]) +
            r'</div>.*?<div class="guest-eps">)(.*?)(</div>)', re.DOTALL)
        mm = pat.search(q)
        if mm:
            if f"Ép. {ep}" not in mm.group(2):
                q = pat.sub(lambda x: x.group(1) + x.group(2) + f" · Ép. {ep} — {title}" + x.group(3), q, count=1)
                qpath.write_text(q, encoding="utf-8")
            print(f"  ✓ qui-sommes-nous.html (invité {m['guest']})")
        else:
            print(f"  ⚠ invité « {m['guest']} » absent de qui-sommes-nous.html — carte à créer manuellement")

    # ── 7. Sitemap ──────────────────────────────────────────────────────────
    spath = ROOT / "sitemap.xml"
    smap = spath.read_text(encoding="utf-8")
    url = f"{BASE}/episodes/{page}"
    if url not in smap:
        line = (f'  <url><loc>{url}</loc><lastmod>{date.today().isoformat()}</lastmod>'
                f'<changefreq>monthly</changefreq><priority>0.9</priority></url>\n')
        anchor = f'<loc>{BASE}/episodes/{prev["page"]}</loc>'
        i = smap.find(anchor)
        if i < 0:
            die("sitemap : entrée épisode précédent introuvable")
        j = smap.rfind("\n", 0, i) + 1
        smap = smap[:j] + line + smap[j:]
        spath.write_text(smap, encoding="utf-8")
    print("  ✓ sitemap.xml")

    # ── 8. Régénérations ────────────────────────────────────────────────────
    run([sys.executable, "scripts/generate_fiches.py"])
    run([sys.executable, "scripts/generate_palmares.py"])
    print("  ✓ fiches + catalogue + palmarès régénérés")

    # ── 9. Validations ──────────────────────────────────────────────────────
    new_html = (ROOT / "episodes" / page).read_text(encoding="utf-8")
    for b in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', new_html, re.DOTALL):
        json.loads(b)
    locs = re.findall(r"<loc>([^<]+)</loc>", spath.read_text(encoding="utf-8"))
    if len(locs) != len(set(locs)):
        die("doublons dans le sitemap !")
    cat = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    entry = next((x for x in cat if x["slug"] == slug), None)
    if not entry or entry.get("mcEpisode") != ep:
        die(f"catalogue : {slug} sans mcEpisode={ep}")
    print("  ✓ validations OK (JSON-LD, sitemap, catalogue)")

    # ── 10. Git ─────────────────────────────────────────────────────────────
    run(["git", "add", "-A"])
    msg = (f"feat: publication episode {ep} - {title}\n\n"
           f"Genere par scripts/publish_episode.py depuis {Path(args.manifest).name}.\n"
           f"Note MediaCritic : {m['note']}/10.\n\n"
           f"Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>\n")
    r = run(["git", "commit", "-m", msg], check=False, capture=True)
    print("  ✓ commit" if r.returncode == 0 else "  = rien à commiter (déjà fait)")

    if args.staging:
        run(["git", "push", "origin", f"HEAD:refs/heads/ep{ep}-staging", "--force"])
        print(f"  ✓ sauvegarde poussée sur ep{ep}-staging")

    if args.push:
        if run(["git", "push", "origin", "gh-pages"], check=False).returncode != 0:
            print("  … push rejeté, rebase sur origin/gh-pages")
            run(["git", "fetch", "origin", "gh-pages"])
            env_ed = {"GIT_EDITOR": "true"}
            if run(["git", "rebase", "origin/gh-pages"], check=False).returncode != 0:
                conflicted = run(["git", "diff", "--name-only", "--diff-filter=U"],
                                 capture=True).stdout.split()
                for f in conflicted:
                    run(["git", "checkout", "--theirs", f])
                run([sys.executable, "scripts/generate_fiches.py"])
                run([sys.executable, "scripts/generate_palmares.py"])
                run(["git", "add", "-A"])
                if run(["git", "-c", "core.editor=true", "rebase", "--continue"],
                       check=False).returncode != 0:
                    run(["git", "rebase", "--abort"])
                    die("rebase impossible — publier manuellement")
            run(["git", "push", "origin", "gh-pages"])
        print("  ✓ PUBLIÉ sur gh-pages")
    else:
        print(f"\nPrêt. Pour publier : python scripts/publish_episode.py {args.manifest} --push")

if __name__ == "__main__":
    main()
