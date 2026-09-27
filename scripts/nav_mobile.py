#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regles CSS de la navigation sur mobile -- source unique.

Constat (27/09/2026) : sur un telephone de 375 px, toute la page defilait
horizontalement sur les episodes et les 8 800 fiches (+280 px), et sur
l'accueil (+52 px).

  - Episodes et fiches : la barre porte six elements non compressibles
    (Accueil, MediaCritic, Annuaire, Classement, Comparateur, Palmares) et
    aucun menu burger. Les trois liens d'annuaire ajoutes en aout l'ont fait
    passer a 655 px. Sur mobile, la rangee de liens devient un bandeau qui
    defile A L'INTERIEUR de la barre : tous les liens restent accessibles,
    la page ne bouge plus. Un fondu a droite signale qu'il y a une suite.
  - Accueil et catalogue : « Ecouter » et « Voir » ont chacun une largeur
    minimale de 100 px. Sur mobile, elle est levee ; en dessous de 420 px,
    « Voir » disparait de la barre -- le lien YouTube reste dans le bloc
    « Le Podcast MediaCritic » juste en dessous.

Utilise par generate_fiches.py (CSS_BLOCK -> assets/fiche.css), par
patch_nav_episodes.py (pages episodes + gabarit) et appliquee une fois a
index.html et catalogue.html, ecrits a la main.
"""

# Pages episodes et fiches : meme structure de nav (nav > .nav-left + etiquette).
CSS_EPISODES_FICHES = (
    "/* mc-nav-mobile */"
    "@media(max-width:640px){"
    "nav{padding:0 14px;gap:10px}"
    ".nav-left{flex:1 1 auto;min-width:0;overflow-x:auto;overflow-y:hidden;"
    "white-space:nowrap;gap:14px;scrollbar-width:none;"
    "-webkit-mask-image:linear-gradient(to right,#000 86%,transparent);"
    "mask-image:linear-gradient(to right,#000 86%,transparent)}"
    ".nav-left::-webkit-scrollbar{display:none}"
    ".nav-left>*{flex-shrink:0}"
    ".nav-ep,.nav-tag{flex-shrink:0}"
    "}"
    # « Episode 47 » et « Podcast » figurent deja dans le badge et le fil
    # d'ariane de la page : sur les plus petits ecrans, on rend la place.
    "@media(max-width:420px){.nav-ep,.nav-tag{display:none}}"
    # Bloc « Note MediaCritic » des episodes (styles en ligne, d'ou les
    # !important) : le texte, element flex, refusait de passer sous la largeur
    # de son plus long mot et debordait de 2 a 5 px a 320 px.
    ".mc-note-block>div{min-width:0}"
    "@media(max-width:420px){.mc-note-block{padding:18px!important;gap:14px!important}}"
)

# Accueil et catalogue : barre avec logo, burger et boutons d'appel.
CSS_ACCUEIL = (
    "/* mc-nav-mobile */"
    "@media(max-width:640px){"
    ".nav-cta,.nav-yt{min-width:0;padding:7px 12px}"
    "}"
    "@media(max-width:420px){"
    ".nav-yt{display:none}"
    ".nav-logo span{font-size:.88rem}"
    "}"
    # A 320 px, « francophones » en 27 px est plus large que l'ecran : le
    # titre poussait la page de 20 px (accueil) et 38 px (catalogue).
    "@media(max-width:380px){"
    ".hero>*{min-width:0}"
    ".hero h1{font-size:1.5rem;hyphens:auto;-webkit-hyphens:auto;overflow-wrap:break-word}"
    "}"
)

def burger_jusqua(px):
    """Le menu burger (add_mobile_menu.py) ne prenait le relais qu'a 640 px.
    Or la barre de l'accueil deborde jusqu'a 1 100 px (+93 px a 1 024, soit
    une tablette en paysage), celle des categories jusqu'a ~760 px, celle de
    contact / qui-sommes-nous jusqu'a ~660 px. Chaque page a donc son seuil,
    mesure : au-dessous, les liens passent dans le menu."""
    return (
        "@media(max-width:%dpx){" % px
        + ".nav-burger{display:block}"
        ".nav-links{display:none;position:absolute;top:100%;left:0;right:0;"
        "background:rgba(6,11,20,.98);backdrop-filter:blur(20px);"
        "border-bottom:1px solid rgba(255,255,255,.08);flex-direction:column;"
        "align-items:stretch;padding:10px 16px 14px;gap:4px;z-index:400}"
        ".nav-links.open{display:flex}"
        ".nav-links a{padding:10px 12px;font-size:.92rem}"
        "}"
    )


# Seuils mesures le 27/09/2026 (largeur a partir de laquelle la barre tient).
CSS_INDEX = CSS_ACCUEIL + burger_jusqua(1180)
# A 320 px, un mot long du titre (« francophones ») depasse l'ecran.
TITRE_320 = ("@media(max-width:380px){h1{hyphens:auto;-webkit-hyphens:auto;"
             "overflow-wrap:break-word}}")
# Contact et qui-sommes-nous ont la meme barre que l'accueil (bouton
# « Ecouter » de 100 px minimum) : memes regles, seuil de burger a elles.
CSS_PAGES_SIMPLES = CSS_ACCUEIL + burger_jusqua(720)
CSS_CATEGORIES = "/* mc-nav-mobile */" + burger_jusqua(820) + TITRE_320

BALISE_ID = "mc-nav-mobile"


def bloc_style(css):
    return '<style id="%s">%s</style>' % (BALISE_ID, css)


def injecter(html, css):
    """Pose (ou remplace) le bloc <style id="mc-nav-mobile"> avant </head>.
    Idempotent : une page deja equipee de la meme version n'est pas touchee."""
    import re
    bloc = bloc_style(css)
    existant = re.search(r'<style id="%s">.*?</style>' % BALISE_ID, html, re.S)
    if existant:
        if existant.group(0) == bloc:
            return html, False
        return html.replace(existant.group(0), bloc, 1), True
    if html.count("</head>") != 1:
        return html, None
    return html.replace("</head>", bloc + "\n</head>", 1), True
