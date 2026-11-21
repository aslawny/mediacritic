#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lecteur du site, « Ma liste d'ecoute » (etape 1, 21/11/2026) : briques communes
aux generateurs (fiches, episodes MediaCritic, podcast du jour, mystere).

Un ELEMENT de liste :
  {id, type: "audio"|"youtube", src, titre, emission, lien, image, date, duree}
  - audio   : fichier PUBLIE par le podcasteur dans son flux RSS (jamais copie
              chez nous ; l'ecoute passe par son hebergeur, stats et pubs
              comprises) ;
  - youtube : identifiant de video, lu par le lecteur OFFICIEL YouTube.

Les titres sont du texte tiers : ils voyagent dans un bloc
<script type="application/json" class="mc-ecoute-data"> (contenu d'element,
« </ » neutralise), JAMAIS dans un attribut. Les boutons ne portent que l'id.
Lecture : assets/liste.js (boutons, liste en localStorage) et la page
ecouter.html (assets/ecouter.js).
"""
import hashlib
import html
import json
import re
import unicodedata

BASE = "https://www.mediacritic.fr"
SCRIPT = '<script defer src="/assets/liste.js"></script>'


def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def _id(src):
    return hashlib.sha1(src.encode("utf-8")).hexdigest()[:12]


def element(ep, emission, lien, image):
    """Episode d'une fiche (episodes_recents) -> element, ou None si rien a lire."""
    if ep.get("audio"):
        src, typ = ep["audio"], "audio"
    elif ep.get("video"):
        src, typ = ep["video"], "youtube"
    else:
        return None
    return {"id": _id(src), "type": typ, "src": src, "titre": ep.get("titre") or "",
            "emission": emission or "", "lien": lien or "", "image": image or "",
            "date": ep.get("date") or "", "duree": ep.get("duree") or None}


def elements_fiche(d):
    lien = f"/fiches/{d.get('slug')}.html"
    out = []
    for ep in d.get("episodes_recents") or []:
        e = element(ep, d.get("title"), lien, d.get("image"))
        if e:
            out.append(e)
    return out


def element_episode(fiche, titre_episode, url_episode=None, emission=None, image=None):
    """Episode cite ailleurs (podcast du jour, mystere) : retrouve dans la
    fiche par son titre ; video YouTube directement depuis son URL."""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([\w-]{11})", url_episode or "")
    if m:
        return element({"video": m.group(1), "titre": titre_episode},
                       emission or fiche.get("title"), f"/fiches/{fiche.get('slug')}.html",
                       image or fiche.get("image"))
    cible = _norm(titre_episode)
    if not cible:
        return None
    for ep in fiche.get("episodes_recents") or []:
        t = _norm(ep.get("titre"))
        if t and (t == cible or t.startswith(cible[:40]) or cible.startswith(t[:40])):
            return element(ep, emission or fiche.get("title"), f"/fiches/{fiche.get('slug')}.html",
                           image or fiche.get("image"))
    return None


def donnees(elements):
    """Bloc JSON a placer dans la page (plusieurs blocs par page possibles)."""
    if not elements:
        return ""
    js = json.dumps({e["id"]: e for e in elements}, ensure_ascii=False, separators=(",", ":"))
    js = js.replace("</", "<\\/").replace("<!--", "<\\!--")
    return f'<script type="application/json" class="mc-ecoute-data">{js}</script>'


def boutons(e, libelle=False):
    """Deux boutons ; aucun texte tiers dans les attributs."""
    i = html.escape(e["id"])
    quoi = "la vidéo" if e["type"] == "youtube" else "l'épisode"
    lecture = "▶ Écouter" if libelle else "▶"
    ajout = "+ Ma liste" if libelle else "+"
    return (f'<span class="mc-ec"><button type="button" class="mc-ec-btn mc-ec-play" data-mc-ec="{i}" '
            f'aria-label="Écouter {quoi} dans le lecteur du site">{lecture}</button>'
            f'<button type="button" class="mc-ec-btn mc-ec-add" data-mc-ec="{i}" '
            f'aria-label="Ajouter {quoi} à ma liste d\'écoute">{ajout}</button></span>')
