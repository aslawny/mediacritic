# -*- coding: utf-8 -*-
"""
Badges MediaCritic a afficher par les emissions (vague 2 SEO, 07/11/2026).

Pourquoi : Search Console ne montrait que 14 domaines pointant vers le site,
presque tous nos propres pages d'episodes. Chaque badge affiche sur le site
d'une emission, sa page Linktree ou sa description est un lien vers sa fiche :
c'est l'emission qui choisit de l'afficher, ce n'est pas du spam de liens.

Trois badges, en SVG (leger, net a toutes les tailles, sans police a
telecharger) :
  - « Critique par MediaCritic — 8,5/10 » : emissions analysees (note reelle) ;
  - « Podcast du jour sur MediaCritic » : emissions mises en avant ;
  - « Reference sur MediaCritic » : toutes les autres fiches.
Les images vivent dans assets/badges/ et le code a coller pointe vers la
fiche de l'emission.
"""
import html

BASE = "https://www.mediacritic.fr"
ORANGE, FOND, TEXTE, GRIS = "#e8622d", "#060b14", "#eef2f7", "#9aa4b2"
POLICE = "Inter,Segoe UI,Helvetica,Arial,sans-serif"


def _cadre(largeur, contenu, titre):
    t = html.escape(titre)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur}" height="64" '
            f'viewBox="0 0 {largeur} 64" role="img" aria-label="{t}"><title>{t}</title>'
            f'<rect width="{largeur}" height="64" rx="12" fill="{FOND}"/>'
            f'<rect x="1" y="1" width="{largeur - 2}" height="62" rx="11" fill="none" '
            f'stroke="{ORANGE}" stroke-opacity=".55"/>'
            # Pastille « MC » a la place du logo : un SVG affiche en <img> ne
            # peut charger aucune image externe.
            f'<rect x="12" y="12" width="40" height="40" rx="9" fill="{ORANGE}"/>'
            f'<text x="32" y="38" text-anchor="middle" font-family="{POLICE}" font-size="16" '
            f'font-weight="800" fill="{FOND}">MC</text>'
            f'{contenu}</svg>')


def svg_note(note):
    n = str(note).replace(".", ",").replace(",0", "")
    return _cadre(250, (
        f'<text x="64" y="27" font-family="{POLICE}" font-size="12" fill="{GRIS}">Critiqué par</text>'
        f'<text x="64" y="46" font-family="{POLICE}" font-size="17" font-weight="700" fill="{TEXTE}">MediaCritic</text>'
        f'<text x="236" y="43" text-anchor="end" font-family="{POLICE}" font-size="24" font-weight="800" '
        f'fill="{ORANGE}">{n}<tspan font-size="14" fill="{GRIS}">/10</tspan></text>'),
        f"Critiqué par MediaCritic : {n}/10")


def svg_du_jour():
    return _cadre(250, (
        f'<text x="64" y="27" font-family="{POLICE}" font-size="12" fill="{GRIS}">Podcast du jour sur</text>'
        f'<text x="64" y="46" font-family="{POLICE}" font-size="17" font-weight="700" fill="{TEXTE}">MediaCritic</text>'
        f'<text x="234" y="42" text-anchor="end" font-size="20">🔥</text>'),
        "Podcast du jour sur MediaCritic")


def svg_reference():
    return _cadre(230, (
        f'<text x="64" y="27" font-family="{POLICE}" font-size="12" fill="{GRIS}">Référencé sur</text>'
        f'<text x="64" y="46" font-family="{POLICE}" font-size="17" font-weight="700" fill="{TEXTE}">MediaCritic</text>'),
        "Référencé sur MediaCritic")


def image_badge(slug, note=None, du_jour=False):
    """(chemin publie, texte alternatif) du badge propre a la fiche."""
    if note is not None:
        n = str(note).replace(".", ",").replace(",0", "")
        return f"assets/badges/note-{slug}.svg", f"Critiqué par MediaCritic : {n}/10"
    if du_jour:
        return "assets/badges/podcast-du-jour.svg", "Podcast du jour sur MediaCritic"
    return "assets/badges/reference.svg", "Référencé sur MediaCritic"


def code_badge(slug, titre, note=None, du_jour=False, cible=None):
    """Code HTML a coller : l'image + le lien. Une emission critiquee pointe
    vers NOTRE CRITIQUE (la page qu'on veut faire monter sur « critique »),
    les autres vers leur fiche."""
    img, alt = image_badge(slug, note, du_jour)
    largeur = 230 if img.endswith("reference.svg") else 250
    cible = cible or f"{BASE}/fiches/{slug}.html"
    return (f'<a href="{cible}" title="{html.escape(titre)} sur MediaCritic">'
            f'<img src="{BASE}/{img}" alt="{html.escape(alt)}" width="{largeur}" height="64" /></a>')


def bloc_fiche(slug, titre, note=None, du_jour=False, prefixe="../", cible=None):
    """Bloc « Affichez le badge » en bas de fiche, pour les editeurs."""
    img, alt = image_badge(slug, note, du_jour)
    code = code_badge(slug, titre, note, du_jour, cible)
    return (
        '  <div class="card bd-card"><h2>🏅 Vous faites cette émission ?</h2>'
        f'<p>Affichez votre badge MediaCritic sur votre site, votre page de liens ou '
        f'la description de vos épisodes.</p>'
        f'<div class="bd-apercu"><img src="{prefixe}{img}" alt="{html.escape(alt)}" '
        f'width="{230 if img.endswith("reference.svg") else 250}" height="64" loading="lazy" /></div>'
        f'<textarea class="bd-code" readonly rows="3" aria-label="Code du badge">{html.escape(code)}</textarea>'
        '<button type="button" class="btn bd-copie" onclick="var t=this.previousElementSibling;'
        "navigator.clipboard.writeText(t.value).then(()=&gt;{this.textContent='Code copié ✓'})\">"
        'Copier le code</button> <a class="bd-lien" href="' + prefixe + 'badges.html">Tous les badges</a></div>')


CSS = """
/* Badges MediaCritic pour les editeurs (vague 2 SEO) */
.bd-card p{color:var(--c-muted2);font-size:.9rem;margin-bottom:12px}
.bd-apercu{margin:4px 0 12px}
.bd-apercu img{display:block;max-width:100%;height:auto}
.bd-code{width:100%;box-sizing:border-box;font:12px/1.5 ui-monospace,Consolas,monospace;color:var(--c-text);background:rgba(255,255,255,.04);border:1px solid var(--c-border);border-radius:8px;padding:10px;resize:vertical}
.bd-copie{margin-top:10px}
.bd-lien{margin-left:12px;font-size:.85rem;color:var(--c-orange)}
"""
