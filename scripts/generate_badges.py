#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Images des badges (assets/badges/*.svg) et page badges.html (vague 2 SEO,
07/11/2026). Voir scripts/badges.py pour le pourquoi.

  - reference.svg, podcast-du-jour.svg : badges generiques ;
  - note-{slug}.svg : un badge par emission critiquee, avec SA note.
Une note qui change (mc_reviews.json) regenere le badge au passage suivant.

Dans REGENERATEURS (publish_episode.py) et dans enrich.yml.
Usage : python scripts/generate_badges.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from badges import BASE, code_badge, svg_du_jour, svg_note, svg_reference  # noqa: E402
from charte import appliquer as charte_appliquer  # noqa: E402

ROOT = Path(__file__).parent.parent
DOSSIER = ROOT / "assets" / "badges"
PAGE = "badges.html"
GA = "G-3W2VTTEWG8"


def ecrire(nom, contenu):
    p = DOSSIER / nom
    if not p.exists() or p.read_text(encoding="utf-8") != contenu:
        p.write_text(contenu, encoding="utf-8")
        return 1
    return 0


def analyses():
    """[(slug, titre, note, url de la critique)] pour chaque fiche notee."""
    revues = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
    cat = {c["slug"]: c for c in json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))}
    page_de = {v["slug"]: v.get("page") for v in revues.values() if v.get("slug")}
    out = []
    for c in cat.values():
        if c.get("mcNote") is None:
            continue
        page = page_de.get(c["slug"])
        out.append((c["slug"], c.get("title") or c["slug"], c["mcNote"],
                    f"{BASE}/episodes/{page}" if page else None))
    return sorted(out, key=lambda x: (-float(x[2]), x[1].lower()))


def main():
    DOSSIER.mkdir(parents=True, exist_ok=True)
    modifies = ecrire("reference.svg", svg_reference()) + ecrire("podcast-du-jour.svg", svg_du_jour())
    liste = analyses()
    for slug, _, note, _ in liste:
        modifies += ecrire(f"note-{slug}.svg", svg_note(note))
    h = lambda s: (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                   .replace('"', "&quot;"))
    ex = liste[0] if liste else ("floodcast", "Floodcast", 8, None)
    exemples = [
        ("Critiqué par MediaCritic", f"assets/badges/note-{ex[0]}.svg",
         "Pour les émissions que nous avons critiquées dans le podcast, avec leur note sur 10. "
         "Le lien mène à notre critique.", code_badge(ex[0], ex[1], ex[2], cible=ex[3])),
        ("Podcast du jour", "assets/badges/podcast-du-jour.svg",
         "Pour les émissions choisies comme podcast du jour sur notre page d'accueil.",
         code_badge("votre-emission", "Votre émission", du_jour=True)),
        ("Référencé sur MediaCritic", "assets/badges/reference.svg",
         "Pour toutes les émissions de l'annuaire : plus de 9 000 podcasts et chaînes YouTube francophones.",
         code_badge("votre-emission", "Votre émission")),
    ]
    blocs = "".join(
        f'<section class="bd-ex"><h2>{h(t)}</h2><p>{h(d)}</p>'
        f'<img src="{img}" alt="{h(t)}" width="250" height="64" loading="lazy" />'
        f'<textarea class="bd-code" readonly rows="3">{h(code)}</textarea></section>'
        for t, img, d, code in exemples)
    critiques = "".join(
        f'<li><a href="{h(url or BASE + "/fiches/" + slug + ".html")}">{h(titre)}</a>'
        f' <span>{str(note).replace(".", ",")}/10</span></li>' for slug, titre, note, url in liste)
    titre = "Badges MediaCritic pour podcasts et chaînes YouTube"
    desc = ("Affichez votre badge MediaCritic : critiqué par MediaCritic avec votre note, podcast "
            "du jour ou référencé dans l'annuaire des podcasts et chaînes YouTube francophones.")
    ld = {"@context": "https://schema.org", "@type": "WebPage", "url": f"{BASE}/{PAGE}",
          "name": titre, "description": desc, "inLanguage": "fr-FR",
          "isPartOf": {"@id": BASE + "/#annuaire"}}
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(titre)}</title>
<meta name="description" content="{h(desc)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{BASE}/{PAGE}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE}/{PAGE}" />
<meta property="og:title" content="{h(titre)}" />
<meta property="og:description" content="{h(desc)}" />
<meta property="og:image" content="{BASE}/assets/banner.png" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
body{{margin:0;background:var(--mc-bg);color:var(--mc-text)}}
.bd-page{{max-width:860px;margin:0 auto;padding:clamp(28px,5vw,56px) clamp(16px,4vw,32px) 56px}}
.bd-page>p{{color:var(--mc-text-2);line-height:1.7}}
.bd-ex{{margin:24px 0;padding:18px;border:1px solid var(--mc-line);border-radius:var(--mc-r-lg);background:var(--mc-surface)}}
.bd-ex p{{color:var(--mc-text-2);margin:0 0 12px}}
.bd-ex img{{display:block;max-width:100%;height:auto;margin-bottom:12px}}
.bd-code{{width:100%;box-sizing:border-box;font:12px/1.5 ui-monospace,Consolas,monospace;color:var(--mc-text);background:var(--mc-bg);border:1px solid var(--mc-line-2);border-radius:8px;padding:10px}}
.bd-liste{{columns:2 260px;padding-left:18px}}
.bd-liste li{{margin:4px 0;break-inside:avoid}}
.bd-liste a{{color:var(--mc-text)}}
.bd-liste span{{color:var(--mc-accent);font-weight:700;margin-left:4px}}
</style>
</head>
<body>
<nav></nav>
<main class="bd-page">
<h1>Les badges MediaCritic</h1>
<p>Votre émission figure dans <a href="catalogue.html">l'annuaire MediaCritic</a> ou a été
critiquée dans notre podcast ? Affichez-le : sur votre site, votre page de liens, la description
de vos épisodes ou de votre chaîne. Le code se copie depuis la fiche de votre émission, avec le
bon lien et, pour les émissions critiquées, votre note.</p>
{blocs}
<section class="bd-ex"><h2>Les émissions critiquées par MediaCritic</h2>
<p>Chacune dispose de son badge avec sa note, à copier depuis sa fiche.</p>
<ul class="bd-liste">{critiques}</ul></section>
</main>
<footer></footer>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>
<script defer src="/assets/partage.js"></script>
</body>
</html>"""
    page, etat = charte_appliquer(page, None)
    assert etat is not None, "charte non appliquée"
    (ROOT / PAGE).write_text(page, encoding="utf-8")
    print(f"badges : {len(liste)} badges de note, {modifies} image(s) mise(s) à jour ; {PAGE} écrit")


if __name__ == "__main__":
    main()
