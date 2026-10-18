#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Charte MediaCritic : en-tete et pied de page uniques -- source unique.

Validee par l'utilisateur le 18/10/2026. Avant, le site comptait sept
en-tetes differents (logo present ou non, « Catalogue » ici, « Annuaire »
la, Classement et Comparateur absents de certaines pages, hauteur de 56 a
64 px) et autant de pieds de page.

Ce module fournit :
  - entete(actif)   : l'en-tete, avec le lien de la rubrique en cours ;
  - pied()          : le pied de page ;
  - appliquer(html, actif, palette) : pose les deux sur une page et y
    charge /assets/mc.css EN DERNIER (la feuille de la charte prime sur
    les styles propres a la page). Idempotent.

Utilise par generate_fiches, generate_categories, generate_palmares,
generate_classement, generate_comparateur et patch_charte.py (pages ecrites
a la main, pages episodes, gabarit). Les styles sont dans assets/mc.css :
ne pas en recopier ici.
"""
import re
from datetime import date

CSS_LIEN = '<link rel="stylesheet" href="/assets/mc.css" />'

# Politique de securite UNIQUE (audit du 18/10/2026). Avant : 7 pages
# seulement avaient une CSP, chacune la sienne ; les 9 428 fiches -- qui
# affichent des avis tiers -- les 50 episodes et les 13 categories n'en
# avaient aucune. GitHub Pages ne permet pas d'en-tete HTTP : la balise meta
# est le seul moyen. `frame-ancestors` y est ignore par les navigateurs, il
# n'est donc pas repris. img-src en https: : les couvertures viennent
# d'Apple, YouTube, Spotify, podCloud... et le bot peut en ajouter.
CSP = ("default-src 'self'; "
       "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://cdn.jsdelivr.net; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src 'self' https://fonts.gstatic.com; "
       "img-src 'self' data: https:; "
       "connect-src 'self' https://www.googletagmanager.com https://*.google-analytics.com "
       "https://*.analytics.google.com https://analytics.google.com; "
       "frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self' mailto:; "
       "upgrade-insecure-requests")
CSP_META = '<meta http-equiv="Content-Security-Policy" content="%s" />' % CSP
DEBUT_H, FIN_H = "<!-- mc-header -->", "<!-- /mc-header -->"
DEBUT_F, FIN_F = "<!-- mc-footer -->", "<!-- /mc-footer -->"

# Rubriques de l'en-tete, dans cet ordre, avec ces libelles et rien d'autre.
RUBRIQUES = [
    ("annuaire", "/catalogue.html", "Annuaire"),
    ("classement", "/classement.html", "Classement"),
    ("palmares", "/palmares.html", "Palmarès"),
    ("comparateur", "/comparer.html", "Comparateur"),
    ("equipe", "/qui-sommes-nous.html", "L'équipe"),
]

SPOTIFY = "https://open.spotify.com/show/5JuffYLQq1q6l7Vh2zvkrV"
APPLE = "https://podcasts.apple.com/fr/podcast/mediacritic/id1853247643"
DEEZER = "https://www.deezer.com/fr/show/1002376672"
YOUTUBE = "https://www.youtube.com/@MediaCriticInc"

# Les 13 pages categories de l'ancien pied de page de l'accueil : le pied
# commun les porte desormais sur toutes les pages (maillage interne).
CATEGORIES = [
    ("histoire", "Histoire"), ("true-crime", "True crime"),
    ("culture-societe", "Culture & société"), ("sciences", "Sciences"),
    ("tech", "Tech"), ("gaming", "Gaming"), ("cinema-series", "Cinéma & séries"),
    ("musique", "Musique"), ("humour", "Humour"), ("sport", "Sport"),
    ("business", "Business"), ("cuisine-gastronomie", "Cuisine"), ("voyage", "Voyage"),
]

_SVG = ' aria-hidden="true" focusable="false"'
ICONE_LOUPE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
               'stroke-linecap="round"' + _SVG + '><circle cx="11" cy="11" r="7"/>'
               '<path d="m20 20-3.5-3.5"/></svg>')
ICONE_MENU = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round"' + _SVG + '><path d="M4 7h16M4 12h16M4 17h16"/></svg>')
ICONE_CASQUE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                'stroke-linecap="round" stroke-linejoin="round"' + _SVG + '>'
                '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="5" height="7" rx="2"/>'
                '<rect x="16" y="14" width="5" height="7" rx="2"/></svg>')

# Icones reprises a l'identique de l'ancien pied de page de l'accueil,
# couleurs retirees : elles prennent la couleur du texte (charte).
SOCIAUX = [('Instagram', 'https://www.instagram.com/mediacritic.inc/', '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'), ('TikTok', 'https://www.tiktok.com/@mediacritic_le_podcast', '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.75a4.85 4.85 0 0 1-1.01-.06z"/></svg>'), ('YouTube', 'https://www.youtube.com/@MediaCriticInc', '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>'), ('X', 'https://x.com/MediaCriticInc', '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'), ('LinkedIn', 'https://www.linkedin.com/in/mediacritic-le-podcast-b890743a1/', '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>')]

_BURGER_JS = ("var h=document.getElementById('mc-header');var o=h.classList.toggle('open');"
              "this.setAttribute('aria-expanded',o);"
              "this.setAttribute('aria-label',o?'Fermer le menu':'Ouvrir le menu')")


# Date et heure de derniere mise a jour du site, dans l'en-tete de TOUTES les
# pages (exigence de l'utilisateur, 18/10/2026 : l'ancien en-tete de
# l'accueil l'affichait, la charte l'avait perdue). Source : l'en-tete HTTP
# Last-Modified de catalog-lite.json, reecrit a chaque passage du bot et a
# chaque publication. Requete HEAD sur la meme origine (autorisee par la CSP).
# Seule source du format : remplit aussi le pied de page (#footer-updated).
_MAJ_JS = (
    "(function(){if(!window.fetch)return;"
    "fetch('/data/catalog-lite.json',{method:'HEAD',cache:'no-cache'}).then(function(r){"
    "var d=new Date(r.headers.get('Last-Modified'));if(isNaN(d))return;"
    "function p(n){return(n<10?'0':'')+n}"
    "var j=p(d.getDate())+'/'+p(d.getMonth()+1),a=d.getFullYear(),h=p(d.getHours())+'h'+p(d.getMinutes());"
    "var e=document.getElementById('nav-updated');"
    "if(e){e.textContent='MàJ '+j+'/'+String(a).slice(-2)+' · '+h;"
    "e.title='Dernière mise à jour du site : '+j+'/'+a+' à '+h;}"
    "var f=document.getElementById('footer-updated');"
    "if(f)f.textContent='Dernière mise à jour : '+j+'/'+a+' à '+h;"
    "}).catch(function(){});})();")


def entete(actif=None):
    liens = "".join(
        '<a href="%s"%s>%s</a>' % (url, ' aria-current="page"' if cle == actif else "", lib)
        for cle, url, lib in RUBRIQUES)
    return "".join([
        DEBUT_H,
        '<header class="mch" id="mc-header"><div class="mch-in">',
        '<div class="mch-brand">',
        '<a class="mch-logo" href="/" aria-label="MediaCritic, accueil">',
        '<img src="/assets/logo.png" alt="" width="28" height="28" /><span>MediaCritic</span></a>',
        # Sous le nom : aucune largeur ajoutee, visible aussi sur telephone.
        '<span class="mch-maj" id="nav-updated"></span>',
        '</div>',
        # Vrai element <nav> (audit SEO du 18/10/2026) : possible depuis que
        # les regles generiques nav{...} des anciennes pages ont ete retirees.
        '<nav class="mch-links" id="mch-menu" aria-label="Navigation principale">',
        liens,
        '<span class="mch-extra"><a href="/contact.html">Contact</a>',
        '<a href="%s" target="_blank" rel="noopener noreferrer">YouTube</a></span>' % YOUTUBE,
        '<span id="mc-partage-slot"></span>',
        '</nav><div class="mch-actions">',
        '<a class="mch-ic" href="/catalogue.html" aria-label="Rechercher dans l&#39;annuaire">',
        ICONE_LOUPE, '</a>',
        '<a class="mc-btn mc-btn-primary mch-listen" href="%s" target="_blank" ' % SPOTIFY,
        'rel="noopener noreferrer" aria-label="Écouter MediaCritic">', ICONE_CASQUE,
        '<span class="mc-lib">Écouter</span></a>',
        '<button type="button" class="mch-burger" aria-controls="mch-menu" aria-expanded="false" ',
        'aria-label="Ouvrir le menu" onclick="%s">' % _BURGER_JS, ICONE_MENU, '</button>',
        '</div></div></header>',
        '<script>', _MAJ_JS, '</script>',
        FIN_H,
    ])


def pied():
    cats = "".join('<li><a href="/categories/%s.html">%s</a></li>' % (s, l) for s, l in CATEGORIES)
    sociaux = "".join(
        '<a href="%s" target="_blank" rel="noopener noreferrer" aria-label="%s">%s</a>' % (h, t, svg)
        for t, h, svg in SOCIAUX)
    ecouter = "".join(
        '<li><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></li>' % (u, l)
        for l, u in (("Spotify", SPOTIFY), ("Apple Podcasts", APPLE), ("Deezer", DEEZER),
                     ("YouTube", YOUTUBE)))
    return "".join([
        DEBUT_F,
        '<footer class="mcf"><div class="mcf-in">',
        '<div class="mcf-brand">',
        '<a class="mcf-logo" href="/"><img src="/assets/logo.png" alt="" width="28" height="28" />',
        '<span>MediaCritic</span></a>',
        '<p>Le podcast qui donne son avis, même quand on ne lui a pas demandé, et l&#39;annuaire des ',
        'podcasts et chaînes YouTube francophones.</p>',
        '<div class="mcf-social">', sociaux, '</div>',
        '</div>',
        '<div><p class="mcf-t">MediaCritic</p><ul>',
        '<li><a href="/catalogue.html">Annuaire</a></li>',
        '<li><a href="/classement.html">Classement</a></li>',
        '<li><a href="/palmares.html">Palmarès des critiques</a></li>',
        '<li><a href="/comparer.html">Comparateur</a></li>',
        '<li><a href="/qui-sommes-nous.html">L&#39;équipe</a></li>',
        '<li><a href="/contact.html">Contact</a></li>',
        '<li><a href="/mentions-legales.html">Mentions légales</a></li>',
        '</ul></div>',
        '<div><p class="mcf-t">Catégories</p><ul>', cats, '</ul></div>',
        '<div><p class="mcf-t">Écouter</p><ul>', ecouter, '</ul></div>',
        '</div>',
        '<div class="mcf-bas">',
        '<p>© %d MediaCritic · <a href="/contact.html">mediacriticinc@gmail.com</a></p>' % date.today().year,
        '<p id="footer-updated"></p>',
        '</div></footer>',
        FIN_F,
    ])


def _remplacer_bloc(html, debut, fin, motif_ancien, neuf):
    """Remplace le bloc balise s'il existe, sinon le premier element ancien.
    Renvoie (html, ok)."""
    i = html.find(debut)
    if i >= 0:
        j = html.find(fin, i)
        if j < 0:
            return html, False
        return html[:i] + neuf + html[j + len(fin):], True
    m = re.search(motif_ancien, html, re.S)
    if not m:
        return html, False
    return html[:m.start()] + neuf + html[m.end():], True


# ---------------------------------------------------------------------------
# Nettoyage des styles morts (etape 3 de la charte)
# ---------------------------------------------------------------------------
# Chaque page embarquait les styles de SON ancien en-tete et de SON ancien pied
# de page. Ils ne visent plus rien, sauf une regle generique `nav{...}` qui
# continuait de s'appliquer au fil d'Ariane des fiches et a la navigation
# precedent/suivant des episodes : rendus collants en haut de page, 64 px de
# haut, contenu etire sur toute la largeur. On retire donc toute regle dont
# TOUS les selecteurs ne visent que l'ancien en-tete ou l'ancien pied.

# Classes encore utilisees qui commencent par « nav- » : precedent/suivant.
_GARDER = ("nav-episodes", "nav-ep-btn")
# Blocs entiers devenus sans objet.
_BLOCS_MORTS = (re.compile(r"<style>/\* mc-burger : menu mobile \*/.*?</style>\s*", re.S),
                re.compile(r'<style id="mc-nav-mobile">.*?</style>\s*', re.S))


def _selecteur_mort(sel):
    s = sel.strip()
    if not s:
        return False
    classes = re.findall(r"\.([a-zA-Z0-9_-]+)", s)
    if any(c in _GARDER for c in classes):
        return False
    if re.match(r"^(nav|footer)(?![a-zA-Z0-9_-])", s):
        return True                      # nav, nav a, footer, footer .x...
    if "#nav-updated" in s:
        return True
    return any(c.startswith(("nav-", "footer-")) for c in classes)


def _nettoyer_regles(css):
    """Parcourt une feuille (accolades imbriquees, commentaires) et retire les
    regles mortes ; une @media videe disparait aussi. Renvoie le CSS."""
    out, i, n = [], 0, len(css)
    while i < n:
        if css.startswith("/*", i):                      # commentaire
            j = css.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(css[i:j]); i = j; continue
        k = css.find("{", i)
        if k < 0:
            out.append(css[i:]); break
        # Un commentaire avant l'accolade : le recopier tel quel.
        c = css.find("/*", i, k)
        if c >= 0:
            out.append(css[i:c]); i = c; continue
        prelude = css[i:k]
        # Fin du bloc (accolades equilibrees)
        prof, j = 1, k + 1
        while j < n and prof:
            if css.startswith("/*", j):
                e = css.find("*/", j + 2); j = n if e < 0 else e + 2; continue
            if css[j] == "{":
                prof += 1
            elif css[j] == "}":
                prof -= 1
            j += 1
        corps = css[k + 1:j - 1]
        tete = prelude.strip()
        if tete.startswith("@media") or tete.startswith("@supports"):
            dedans = _nettoyer_regles(corps)
            if dedans.strip():
                out.append(prelude + "{" + dedans + "}")
            else:
                out.append(prelude[:len(prelude) - len(prelude.lstrip())])
        elif tete.startswith("@"):
            out.append(css[i:j])                          # @keyframes, @font-face...
        else:
            sels = tete.split(",")
            vivants = [s for s in sels if not _selecteur_mort(s)]
            if len(vivants) == len(sels):
                out.append(css[i:j])
            elif vivants:
                blanc = prelude[:len(prelude) - len(prelude.lstrip())]
                out.append(blanc + ",".join(v.strip() for v in vivants) + "{" + corps + "}")
            else:
                out.append(prelude[:len(prelude) - len(prelude.lstrip())])
        i = j
    return "".join(out)


def nettoyer_feuille(css):
    """Pour une feuille externe (assets/fiche.css)."""
    return _nettoyer_regles(css)


def nettoyer_html(html):
    for motif in _BLOCS_MORTS:
        html = motif.sub("", html)
    return re.sub(r"(<style[^>]*>)(.*?)(</style>)",
                  lambda m: m.group(1) + _nettoyer_regles(m.group(2)) + m.group(3), html, flags=re.S)


def appliquer(html, actif=None, palette=None):
    """Pose l'en-tete, le pied de page et la feuille de la charte, et retire
    les styles morts de l'ancien en-tete / pied de page.
    Renvoie (html, etat) : True modifie, False deja conforme, None page non
    reconnue (on ne touche a rien plutot que de casser)."""
    orig = html
    # L'ancien en-tete est TOUJOURS le premier <nav> nu de la page : les autres
    # nav (fil d'Ariane, precedent/suivant des episodes) portent une classe.
    html, ok_h = _remplacer_bloc(html, DEBUT_H, FIN_H, r"<nav>.*?</nav>", entete(actif))
    html, ok_f = _remplacer_bloc(html, DEBUT_F, FIN_F, r"<footer[^>]*>.*?</footer>", pied())
    if not (ok_h and ok_f):
        return orig, None
    html = nettoyer_html(html)
    # CSP unique : on retire celle de la page et on pose la notre juste apres
    # <meta charset>, avant tout script ou feuille de style.
    html = re.sub(r'\s*<meta http-equiv="Content-Security-Policy"[^>]*>', "", html)
    m = re.search(r"<meta charset=[^>]*>", html, re.I)
    if not m:
        return orig, None
    html = html[:m.end()] + "\n" + CSP_META + html[m.end():]
    # Feuille de la charte : derniere chose du <head>, pour primer.
    html = html.replace(CSS_LIEN + "\n", "").replace(CSS_LIEN, "")
    if html.count("</head>") != 1:
        return orig, None
    html = html.replace("</head>", CSS_LIEN + "\n</head>", 1)
    # Palette b : pages episodes et fiches, ou muted/muted2 ont le sens inverse.
    html = re.sub(r'(<html\b[^>]*?)\s+data-mc-pal="[^"]*"', r"\1", html, count=1)
    if palette:
        html = re.sub(r"<html\b", '<html data-mc-pal="%s"' % palette, html, count=1)
    return html, html != orig
