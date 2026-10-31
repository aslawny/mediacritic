#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rendu du « podcast du jour » a partir de data/du_jour.json (ecrit par
du_jour.py) :

  - bloc de l'accueil, entre <!-- du-jour --> et <!-- /du-jour --> dans
    index.html : HTML statique, lisible sans JavaScript ;
  - podcast-du-jour.html : la selection du jour + l'archive. UNE page qui
    s'enrichit chaque jour, plutot qu'une page par jour (365 pages minces par
    an = remplissage aux yeux de Google) ;
  - kit-du-jour.html : textes prets a publier pour chaque reseau + visuels.
    noindex, hors sitemap, lie nulle part : c'est l'outil de l'equipe
    (phase 1 : publication a la main, voir le skill mediacritic-site) ;
  - assets/du-jour/AAAA-MM-JJ.jpg (1200x630) et -carre.jpg (1080x1080).
    30 jours conserves.

Idempotent, sans reseau sauf pour telecharger la couverture du visuel.
Dans REGENERATEURS : suit les changements de charte comme les autres pages.

Usage : python scripts/generate_du_jour.py
"""
import html
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charte import appliquer as charte_appliquer  # noqa: E402

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"
PAGE = "podcast-du-jour.html"
KIT = "kit-du-jour.html"
VISUELS = ROOT / "assets" / "du-jour"
GARDER_VISUELS = 30
DEBUT, FIN = "<!-- du-jour -->", "<!-- /du-jour -->"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]


def h(s):
    return html.escape(str(s or ""), quote=True)


def date_fr(iso, annee=False):
    d = date.fromisoformat(iso)
    j = "1er" if d.day == 1 else str(d.day)
    return f"{j} {MOIS[d.month - 1]}" + (f" {d.year}" if annee else "")


def libelle(c):
    """« Le podcast du jour », « La chaîne du jour », « La pépite du jour »."""
    if c.get("mode") == "pepite":
        return "💎 La pépite du jour"
    return "🔥 La chaîne du jour" if c.get("type") == "youtube" else "🔥 Le podcast du jour"


def cover(url, taille=600):
    url = url or ""
    url = re.sub(r"/\d+x\d+bb\.(png|jpg|jpeg|webp)$", f"/{taille}x{taille}bb.jpg", url)
    url = re.sub(r"=s\d+(-[^/]*)?$", "=s800", url)
    return url


def label_indep(c, prefixe=""):
    if not c.get("independant"):
        return ""
    return (f'<a class="mc-indep" href="{prefixe}podcasts-independants.html" '
            'title="Publié hors radios, presse, studios et institutions : voir le guide">'
            'Indépendant</a>')


def sections_html(c):
    """« Pourquoi ce choix » : TROIS sections et rien d'autre (demande de
    l'utilisateur, 28/10/2026) — l'actu qui a fait le buzz, l'émission,
    pourquoi l'écouter. Les règles de sélection ne s'affichent jamais."""
    blocs = "".join(f'<div class="mcj-s"><p class="mcj-s-t">{h(t)}</p><p class="mcj-s-p">{h(v)}</p></div>'
                    for t, v in c["sections"])
    return f'<div class="mcj-raisons"><p class="mcj-raisons-t">Pourquoi ce choix</p>{blocs}</div>'


def carte(c, prefixe="", titre_tag="h2", lien_archive=True):
    """Le bloc mis en avant (accueil et haut de l'archive)."""
    ep = c.get("episode") or {}
    boutons = []
    if ep.get("url"):
        lib = "▶ Voir la vidéo" if c.get("type") == "youtube" else "▶ Écouter l'épisode"
        boutons.append(f'<a class="mcj-btn mcj-btn-1" href="{h(ep["url"])}" target="_blank" '
                       f'rel="noopener">{lib}</a>')
    boutons.append(f'<a class="mcj-btn" href="{prefixe}fiches/{h(c["slug"])}.html">Voir la fiche</a>')
    if lien_archive:
        boutons.append(f'<a class="mcj-btn mcj-btn-lien" href="{prefixe}{PAGE}">Les sélections précédentes →</a>')
    img = cover(c.get("image"))
    vign = (f'<img src="{h(img)}" alt="{h(c["titre"])}" width="160" height="160" loading="eager" decoding="async" />'
            if img else '<span class="mcj-ph">🎙️</span>')
    note = (f'<span class="mcj-note">★ {str(c["mcNote"]).replace(".", ",")}/10 MediaCritic</span>'
            if c.get("mcNote") else "")
    return (
        f'<article class="mcj" aria-label="{h(libelle(c))}">'
        f'<a class="mcj-cover" href="{prefixe}fiches/{h(c["slug"])}.html">{vign}</a>'
        f'<div class="mcj-txt">'
        f'<p class="mcj-eyebrow">{h(libelle(c))} · {h(date_fr(c["date"]))}</p>'
        f'<{titre_tag} class="mcj-titre"><a href="{prefixe}fiches/{h(c["slug"])}.html">{h(c["titre"])}</a></{titre_tag}>'
        f'<p class="mcj-labels">{label_indep(c, prefixe)}{note}</p>'
        + (sections_html(c) if c.get("sections") else f'<p class="mcj-pourquoi">{h(c["pourquoi"])}</p>')
        + f'<div class="mcj-actions">{"".join(boutons)}</div>'
        f'</div></article>')


# --------------------------------------------------------------------------
# Accueil
# --------------------------------------------------------------------------
def bloc_accueil(dernier):
    return (DEBUT + '\n<section class="mcj-zone" aria-label="Le podcast du jour">'
            + carte(dernier, titre_tag="h2") + '</section>\n' + FIN)


def maj_accueil(dernier):
    p = ROOT / "index.html"
    s = io.open(p, encoding="utf-8", newline="").read()   # fins de ligne conservees
    neuf = bloc_accueil(dernier)
    if DEBUT in s:
        s2 = re.sub(re.escape(DEBUT) + ".*?" + re.escape(FIN), lambda m: neuf, s, flags=re.S)
    else:
        ancre = "<!-- SEARCH + FILTERS -->"
        if ancre not in s:
            print("  ! index.html : ancre du bloc introuvable, accueil non modifié")
            return
        s2 = s.replace(ancre, neuf + "\n\n" + ancre, 1)
    if s2 != s:
        io.open(p, "w", encoding="utf-8", newline="").write(s2)
        print("  index.html : bloc du jour mis à jour")


# --------------------------------------------------------------------------
# Page archive
# --------------------------------------------------------------------------
def page_archive(hist):
    dernier = hist[0]
    lignes = []
    for c in hist[1:120]:
        ep = c.get("episode") or {}
        quoi = (f'« {h(c.get("sujet"))} » — {h(ep.get("titre"))}' if c.get("mode") == "actu"
                else "Pépite indépendante")
        lignes.append(
            f'<li class="mcj-l"><span class="mcj-l-date">{h(date_fr(c["date"], True))}</span>'
            f'<a href="fiches/{h(c["slug"])}.html">{h(c["titre"])}</a>{label_indep(c)}'
            f'<span class="mcj-l-quoi">{quoi}</span></li>')
    archive = (f'<section class="mcj-archive"><h2>Les sélections précédentes</h2>'
               f'<ol class="mcj-liste">{"".join(lignes)}</ol></section>' if lignes else "")
    titre = "Le podcast du jour : l'actu en podcast et sur YouTube"
    desc = ("Chaque matin, le podcast ou la chaîne YouTube francophone qui parle de "
            "l'actualité, preuve à l'appui : l'épisode, sa date, son lien.")
    og = f"{BASE}/assets/du-jour/{dernier['date']}.jpg" \
        if (VISUELS / f"{dernier['date']}.jpg").exists() else f"{BASE}/assets/banner.png"
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": f"{BASE}/{PAGE}", "url": f"{BASE}/{PAGE}",
         "name": titre, "description": desc, "inLanguage": "fr-FR",
         "isPartOf": {"@id": BASE + "/#annuaire"}},
        {"@type": "ItemList", "name": "Les podcasts du jour", "numberOfItems": min(len(hist), 30),
         "itemListElement": [{"@type": "ListItem", "position": i + 1,
                              "url": f"{BASE}/fiches/{c['slug']}.html", "name": c["titre"]}
                             for i, c in enumerate(hist[:30])]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Le podcast du jour",
             "item": f"{BASE}/{PAGE}"}]},
    ]}
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{h(titre)}</title>
<meta name="description" content="{h(desc)}" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
<link rel="canonical" href="{BASE}/{PAGE}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{BASE}/{PAGE}" />
<meta property="og:title" content="{h(libelle(dernier))} : {h(dernier['titre'])}" />
<meta property="og:description" content="{h(dernier['pourquoi'])}" />
<meta property="og:image" content="{og}" />
<meta property="og:locale" content="fr_FR" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{h(libelle(dernier))} : {h(dernier['titre'])}" />
<meta name="twitter:description" content="{h(dernier['pourquoi'])}" />
<meta name="twitter:image" content="{og}" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet" />
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
body{{margin:0;background:var(--mc-bg);color:var(--mc-text)}}
a{{color:inherit}}
.mcj-page{{max-width:900px;margin:0 auto;padding:clamp(28px,5vw,56px) clamp(16px,4vw,32px) 56px}}
.mcj-page>p{{color:var(--mc-text-2);line-height:1.7;margin:0 0 14px}}
.mcj-page>p a{{color:var(--mc-text);text-decoration:underline;text-underline-offset:2px}}
.mcj-methode{{font-size:14px}}
</style>
</head>
<body>
<nav></nav>
<main class="mcj-page">
<h1>Le podcast du jour</h1>
<p>Chaque jour, l'actu qui fait le buzz et l'émission de <a href="catalogue.html">notre
annuaire</a> qui en parle : un podcast ou une chaîne YouTube francophone à écouter pour aller
plus loin que les gros titres.</p>
<section class="mcj-zone">{carte(dernier, titre_tag="h2", lien_archive=False)}</section>
{archive}
</main>
<footer></footer>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>
<script defer src="/assets/partage.js"></script>
</body>
</html>"""
    page, etat = charte_appliquer(page, "accueil")
    assert etat is not None, "charte non appliquée (en-tête ou pied introuvable)"
    (ROOT / PAGE).write_text(page, encoding="utf-8")
    print(f"  {PAGE} : {len(hist)} sélection(s)")


# --------------------------------------------------------------------------
# Kit reseaux (phase 1 : publication a la main)
# --------------------------------------------------------------------------
NOMS_RESEAUX = {"instagram": "Instagram", "x": "X", "tiktok": "TikTok", "facebook": "Facebook",
                "linkedin": "LinkedIn", "youtube": "YouTube", "threads": "Threads",
                "bluesky": "Bluesky", "twitch": "Twitch"}


def tags(c, reseau):
    """« @compte » a coller dans le post. Threads reprend les noms Instagram
    (meme identite), faute de compte Threads declare."""
    r = c.get("reseaux") or {}
    comptes = r.get(reseau) or (r.get("instagram") if reseau == "threads" else None) or []
    if reseau == "linkedin":
        # LinkedIn mentionne par le NOM : « in/julien-moch-5b920281 » ->
        # « @Julien Moch » (taper @ puis choisir la personne proposee).
        noms = []
        for x in comptes:
            n = x["compte"].split("/", 1)[-1]
            n = re.sub(r"-[0-9a-f]{6,}$", "", n).replace("-", " ").strip()
            noms.append("@" + n.title())
        return " ".join(noms)
    return " ".join("@" + x["compte"] for x in comptes)


def textes_reseaux(c):
    def lien(src):
        return (f"{BASE}/{PAGE}?utm_source={src}&utm_medium=social&utm_campaign=du-jour")
    ep = c.get("episode") or {}
    indep = " (podcast indépendant)" if c.get("independant") and c.get("type") != "youtube" else ""
    if c.get("mode") == "actu":
        accroche = f"« {c['sujet']} » fait l'actu. {c['titre']}{indep} en parle dans « {ep.get('titre')} »."
    else:
        accroche = c["pourquoi"]
    tete = libelle(c)
    court = accroche if len(accroche) <= 190 else accroche[:187].rsplit(" ", 1)[0] + "…"
    t = lambda r: (f"\n\n{tags(c, r)}" if tags(c, r) else "")
    return {
        "X": f"{tete} : {c['titre']}\n\n{court}{t('x')}\n\n👉 {lien('x')}\n#podcast",
        "Bluesky": f"{tete} : {c['titre']}\n\n{court}{t('bluesky')}\n\n{lien('bluesky')}",
        "Threads": f"{tete} : {c['titre']}\n\n{accroche}{t('threads')}\n\n{lien('threads')}",
        "TikTok": (f"{tete} : {c['titre']}\n\n{court}{t('tiktok')}\n\n🔗 mediacritic.fr\n"
                   f"#podcast #podcastdujour #mediacritic"),
        "Facebook": (f"{tete} : {c['titre']}\n\n{accroche}\n\n{c.get('presentation') or ''}{t('facebook')}"
                     f"\n\n👉 {lien('facebook')}"),
        "LinkedIn": (f"{tete} : {c['titre']}\n\n{accroche}\n\n{c.get('presentation') or ''}{t('linkedin')}\n\n"
                     f"Chaque jour, MediaCritic vous propose l'émission qui parle de l'actu du moment.\n\n"
                     f"👉 {lien('linkedin')}\n\n#podcast #podcastfrançais #actualité"),
        "Instagram": (f"{tete} : {c['titre']}\n\n{accroche}\n\n{c.get('presentation') or ''}{t('instagram')}\n\n"
                      f"🔗 Lien en bio — mediacritic.fr\n\n#podcast #podcastfrancais #podcastdujour "
                      f"#ecouterdespodcasts #mediacritic"),
    }


def bloc_a_taguer(c):
    """Comptes officiels de l'emission, reseau par reseau, avec leur source."""
    r = c.get("reseaux") or {}
    if not r:
        return ('<section class="kit-b kit-tags"><h2>🏷️ À taguer</h2><p>Aucun compte trouvé dans les '
                'sources officielles de l\'émission (page YouTube, flux, site, description). '
                'Rien n\'est deviné : à chercher à la main si besoin.</p></section>')
    lignes = "".join(
        f'<li><strong>{h(NOMS_RESEAUX.get(res, res))}</strong> '
        + ", ".join(f'<a href="{h(x["url"])}" target="_blank" rel="noopener">'
                    f'{h(x["compte"].split("/", 1)[-1]) if res == "linkedin" else "@" + h(x["compte"])}</a> '
                    f'<span class="kit-src">({h(x["source"])})</span>' for x in comptes)
        + "</li>" for res, comptes in r.items())
    return (f'<section class="kit-b kit-tags"><h2>🏷️ À taguer</h2><ul>{lignes}</ul>'
            '<p class="kit-src">Comptes relevés dans les sources officielles de l\'émission ; ils sont '
            'déjà insérés dans les textes ci-dessous. Sur Facebook et LinkedIn, retaper le @ pour que '
            'le réseau propose le compte et transforme la mention en lien.</p>'
            '</section>')


def page_kit(c):
    t = textes_reseaux(c)
    blocs = "".join(
        f'<section class="kit-b"><h2>{h(r)}</h2><textarea readonly rows="8" id="t-{i}">{h(v)}</textarea>'
        f'<button type="button" onclick="navigator.clipboard.writeText(document.getElementById(\'t-{i}\').value);'
        f'this.textContent=\'Copié ✓\'">Copier</button></section>'
        for i, (r, v) in enumerate(t.items()))
    visuels = ""
    for suffixe, lib in (("", "Visuel 1200×630 (X, Facebook, LinkedIn, Bluesky)"),
                         ("-carre", "Visuel 1080×1080 (Instagram, Threads)")):
        f = f"assets/du-jour/{c['date']}{suffixe}.jpg"
        if (ROOT / f).exists():
            visuels += (f'<figure><img src="{f}" alt="{h(lib)}" loading="lazy" />'
                        f'<figcaption><a href="{f}" download>Télécharger — {h(lib)}</a></figcaption></figure>')
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Kit du jour | MediaCritic</title>
<meta name="robots" content="noindex, nofollow" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<style>
body{{margin:0;background:var(--mc-bg);color:var(--mc-text)}}
.kit{{max-width:820px;margin:0 auto;padding:32px 16px 56px}}
.kit>p{{color:var(--mc-text-2);line-height:1.6}}
.kit-b{{margin:20px 0;padding:16px;border:1px solid var(--mc-line);border-radius:12px;background:var(--mc-surface)}}
.kit-b h2{{margin:0 0 8px}}
.kit-b textarea{{width:100%;box-sizing:border-box;background:var(--mc-bg);color:var(--mc-text);border:1px solid var(--mc-line-2);border-radius:8px;padding:10px;font:inherit;font-size:14px}}
.kit-b button{{margin-top:8px;padding:8px 16px;border-radius:8px;border:0;background:var(--mc-accent);color:var(--mc-on-accent);font-weight:700;cursor:pointer}}
.kit figure{{margin:16px 0}}
.kit figure img{{max-width:100%;border-radius:12px;display:block}}
.kit figcaption a{{color:var(--mc-text)}}
.kit-tags ul{{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px}}
.kit-tags a{{color:var(--mc-accent)}}
.kit-src{{color:var(--mc-text-3);font-size:13px}}
</style>
</head>
<body>
<nav></nav>
<main class="kit">
<h1>Kit réseaux du {h(date_fr(c['date'], True))}</h1>
<p>Page de travail de l'équipe (non référencée). Textes prêts à copier, visuels à télécharger.
Chaque lien porte un marqueur de suivi par réseau, visible dans Google Analytics
(campagne « du-jour »).</p>
{carte(c, titre_tag="h2", lien_archive=False)}
{bloc_a_taguer(c)}
{visuels}
{blocs}
</main>
<footer></footer>
<script defer src="/assets/partage.js"></script>
</body>
</html>"""
    page, etat = charte_appliquer(page, None)
    assert etat is not None
    (ROOT / KIT).write_text(page, encoding="utf-8")
    print(f"  {KIT} : {len(t)} textes")


# --------------------------------------------------------------------------
# Visuels
# --------------------------------------------------------------------------
def _police(taille, gras=True):
    from PIL import ImageFont
    for f in (["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "C:/Windows/Fonts/arialbd.ttf"] if gras else
              ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "C:/Windows/Fonts/arial.ttf"]):
        try:
            return ImageFont.truetype(f, taille)
        except Exception:
            continue
    return ImageFont.load_default()


def _lignes(draw, texte, police, largeur, maxi):
    mots, lignes, cur = texte.split(), [], ""
    for m in mots:
        essai = (cur + " " + m).strip()
        if draw.textlength(essai, font=police) <= largeur:
            cur = essai
        else:
            lignes.append(cur)
            cur = m
    if cur:
        lignes.append(cur)
    if len(lignes) > maxi:
        lignes = lignes[:maxi]
        lignes[-1] = lignes[-1].rstrip(" ,.;:") + "…"
    return lignes


def visuels(c):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  Pillow absent : visuels non générés")
        return
    VISUELS.mkdir(parents=True, exist_ok=True)
    pochette = None
    url = cover(c.get("image"))
    if url:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                pochette = Image.open(io.BytesIO(r.read())).convert("RGB")
        except Exception as e:
            print(f"  ! couverture non téléchargée : {e}")
    orange, texte, gris, vert = (232, 98, 45), (238, 242, 247), (170, 180, 195), (52, 199, 123)
    ep = c.get("episode") or {}
    sous_titre = (f"« {c['sujet']} » fait l'actu" if c.get("mode") == "actu" else "Pépite indépendante")
    detail = (f"Dans « {ep.get('titre')} »" if c.get("mode") == "actu" else
              (c.get("presentation") or ""))
    for suffixe, (W, H) in (("", (1200, 630)), ("-carre", (1080, 1080))):
        im = Image.new("RGB", (W, H), (6, 11, 20))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 10], fill=orange)
        marge = 64
        if suffixe:   # carre : pochette en haut, texte dessous
            cote = 420
            x0, y0 = (W - cote) // 2, 90
            zone_x, zone_w, y = marge, W - 2 * marge, y0 + cote + 50
        else:         # paysage : pochette a gauche
            cote = 400
            x0, y0 = marge, (H - cote) // 2
            zone_x, zone_w, y = x0 + cote + 56, W - (x0 + cote + 56) - marge, 92
        if pochette:
            im.paste(pochette.resize((cote, cote)), (x0, y0))
        else:
            d.rectangle([x0, y0, x0 + cote, y0 + cote], fill=(19, 35, 59))
        f_eye, f_tit, f_sub, f_det = _police(30), _police(54 if not suffixe else 58), _police(34), _police(26, False)
        d.text((zone_x, y), libelle(c).split(" ", 1)[1].upper(), font=f_eye, fill=orange)
        y += 52
        for l in _lignes(d, c["titre"], f_tit, zone_w, 2):
            d.text((zone_x, y), l, font=f_tit, fill=texte)
            y += 66
        if c.get("independant"):
            lab = "INDÉPENDANT"
            lw = d.textlength(lab, font=_police(22))
            d.rounded_rectangle([zone_x, y + 4, zone_x + lw + 28, y + 40], radius=6, fill=vert)
            d.text((zone_x + 14, y + 9), lab, font=_police(22), fill=(6, 32, 18))
            y += 56
        for l in _lignes(d, sous_titre, f_sub, zone_w, 2):
            d.text((zone_x, y), l, font=f_sub, fill=texte)
            y += 44
        for l in _lignes(d, detail, f_det, zone_w, 3 if not suffixe else 2):
            d.text((zone_x, y), l, font=f_det, fill=gris)
            y += 34
        pied = "mediacritic.fr"
        d.text((W - marge - d.textlength(pied, font=_police(28)), H - 58), pied, font=_police(28), fill=orange)
        im.save(VISUELS / f"{c['date']}{suffixe}.jpg", "JPEG", quality=84, optimize=True)
    # Menage : 30 jours de visuels suffisent (le kit ne sert que le jour meme).
    limite = (date.fromisoformat(c["date"]) - timedelta(days=GARDER_VISUELS)).isoformat()
    for f in VISUELS.glob("*.jpg"):
        if f.name[:10] < limite:
            f.unlink()
    print(f"  visuels : assets/du-jour/{c['date']}.jpg et -carre.jpg")


def maj_sitemap(jour):
    p = ROOT / "sitemap.xml"
    s = io.open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in s else "\n"
    url = f"{BASE}/{PAGE}"
    ligne = (f"  <url><loc>{url}</loc><lastmod>{jour}</lastmod>"
             f"<changefreq>daily</changefreq><priority>0.8</priority></url>")
    if f"<loc>{url}</loc>" in s:
        s2 = re.sub(r"  <url><loc>" + re.escape(url) + r"</loc>.*?</url>", lambda m: ligne, s)
    else:
        s2 = s.replace("</urlset>", ligne + nl + "</urlset>")
    if s2 != s:
        io.open(p, "w", encoding="utf-8", newline="").write(s2)


def main():
    src = ROOT / "data" / "du_jour.json"
    if not src.exists():
        print("data/du_jour.json absent : rien à rendre")
        return
    hist = json.loads(src.read_text(encoding="utf-8"))["historique"]
    if not hist:
        return
    dernier = hist[0]
    if not (VISUELS / f"{dernier['date']}.jpg").exists():
        visuels(dernier)
    maj_accueil(dernier)
    page_archive(hist)
    page_kit(dernier)
    maj_sitemap(dernier["date"])


if __name__ == "__main__":
    main()
