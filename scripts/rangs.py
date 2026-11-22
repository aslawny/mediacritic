#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulletin du createur (22/11/2026) : rendu de l'encart « 🏆 N° x » d'une fiche.

Source : data/rangs.json, ecrit par scripts/generate_rangs.py, qui LIT les
classements sur les pages publiees (top 10 des categories, classement.html,
chaines-youtube.html, podcasts-independants.html). Une fiche n'affiche donc
jamais un rang qu'aucune page du site ne montre.

Deux appelants, MEME rendu (sinon chaque passage reecrirait les fiches) :
  - generate_fiches.py (gabarit) ;
  - generate_rangs.py (mise a jour des fiches deja ecrites).
Marqueurs : <!-- mc-rang -->…<!-- /mc-rang --> (toujours presents, vides
s'il n'y a pas de rang).
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
SOURCE = ROOT / "data" / "rangs.json"
DEBUT, FIN = "<!-- mc-rang -->", "<!-- /mc-rang -->"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
_cache = None


def h(s):
    return html.escape(str(s or ""), quote=True)


def donnees(recharger=False):
    global _cache
    if _cache is None or recharger:
        try:
            _cache = json.loads(SOURCE.read_text(encoding="utf-8"))
        except Exception:
            _cache = {"rangs": {}}
    return _cache


def rang(slug):
    return (donnees().get("rangs") or {}).get(slug)


def _date_fr(iso):
    a, m, j = iso.split("-")
    return f"{int(j)} {MOIS[int(m) - 1]}"


# Partage : feuille de partage du telephone, sinon copie du lien.
_PARTAGE_JS = ("var u=location.href.split('#')[0],t=this.getAttribute('data-texte');"
               "if(navigator.share){navigator.share({title:document.title,text:t,url:u}).catch(function(){});}"
               "else if(navigator.clipboard){navigator.clipboard.writeText(t+' '+u);this.textContent='Lien copié ✓';}"
               "try{gtag('event','rang_partager');}catch(e){}")


def bloc(slug):
    """Encart entre marqueurs (vide si pas de rang)."""
    r = rang(slug)
    if not r:
        return DEBUT + FIN
    progres = ""
    if r.get("progression"):
        p = r["progression"]
        if p.get("nouveau"):
            progres = f'<span class="mc-rang-prog">✨ Nouvelle entrée depuis le {h(_date_fr(p["depuis"]))}</span>'
        elif p.get("places", 0) > 0:
            n = p["places"]
            progres = (f'<span class="mc-rang-prog">↑ {n} place{"s" if n > 1 else ""} '
                       f'depuis le {h(_date_fr(p["depuis"]))}</span>')
    texte = f"N° {r['rang']} · {r['liste']} — sur MediaCritic"
    return (
        DEBUT
        + '<div class="card mc-rang">'
        + '<p class="mc-rang-titre"><span class="mc-rang-ico" aria-hidden="true">🏆</span>'
        + f'<span><strong class="mc-rang-n">N° {h(r["rang"])}</strong> '
        + f'<a href="../{h(r["url"])}">{h(r["liste"])}</a></span></p>'
        + (f'<p class="mc-rang-src">{h(r["source"])}</p>' if r.get("source") else "")
        + '<p class="mc-rang-actions">' + progres
        + f'<button type="button" class="mc-rang-partager" data-texte="{h(texte)}" onclick="{h(_PARTAGE_JS)}">'
        + 'Partager ce classement</button></p>'
        + '</div>'
        + FIN)


def og(slug, defaut):
    """Image de partage : visuel du rang pour le podium (N° 1 a 3), sinon la pochette."""
    r = rang(slug)
    if r and r.get("image"):
        return f"{BASE}/{r['image']}"
    return defaut
