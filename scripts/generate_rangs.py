#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulletin du createur (22/11/2026, valide par l'utilisateur) : chaque fiche
bien classee affiche son meilleur rang, avec sa source, et le partage.

PRINCIPE : on ne recalcule AUCUN classement. On LIT les listes publiees par
les autres generateurs, qui font foi :
  - categories/*.html, section #top (« Les 10 meilleurs podcasts … ») ;
  - classement.html (mieux notes, plus populaires, chaines) ;
  - chaines-youtube.html (top 50, independantes, top 10 par theme) ;
  - podcasts-independants.html (mieux notes, plus ecoutes, chaines).
Une fiche n'affiche donc jamais un rang qu'aucune page ne montre. Sections
ignorees : nos propres critiques (pepites, critiquees : c'est notre note,
deja affichee), la page Desirs & intimite.
Meilleur rang = plus petit numero ; a egalite, la liste la plus large.
Pas de rang affiche pour les fiches complotistes ni Desirs & intimite.

Sorties :
  - data/rangs.json : rang affiche par fiche (lu par scripts/rangs.py) ;
  - data/_rangs.json : HISTORIQUE (une photo par semaine, 12 gardees, non
    publie) -> progressions « ↑ 4 places depuis le … » et future page
    « Ça monte » ;
  - assets/rangs/{slug}.jpg : image de partage (1200x630) du podium (N° 1-3) ;
  - fiches/{slug}.html : encart et og:image mis a jour SANS toucher au
    sitemap (un rang n'est pas une mise a jour du contenu).

Dans REGENERATEURS (apres les pages de classement) et dans enrich.yml.
Usage : python scripts/generate_rangs.py [--sans-images]
"""
import argparse
import os
import hashlib
import io
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rangs  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
HISTO = DATA / "_rangs.json"
IMAGES = ROOT / "assets" / "rangs"
SIG_IMAGES = DATA / "_rangs_images.json"
GARDER_SEMAINES = 12
PODIUM = 3
IGNORER_SECTIONS = {"pepites", "critiquees"}
PAGES = ["classement.html", "chaines-youtube.html", "podcasts-independants.html"]
# Largeur de liste a egalite de rang : general > independants > theme.
PORTEE = {"classement.html": 3, "chaines-youtube.html#plus-suivies": 3,
          "podcasts-independants.html": 2, "chaines-youtube.html#independantes": 2}


def texte(s):
    s = re.sub(r"<[^>]+>", "", s)
    return " ".join(__import__("html").unescape(s).split())


def lire_listes():
    """[{id, url, titre, source, slugs[]}] lues sur les pages publiees."""
    listes = []
    fichiers = [(p, p) for p in PAGES]
    fichiers += [(f"categories/{f.name}", f"categories/{f.name}")
                 for f in sorted((ROOT / "categories").glob("*.html"))
                 if f.name != "podcasts-erotiques.html"]
    for rel, url in fichiers:
        f = ROOT / rel
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r'<section class="[^"]*" id="([^"]+)"><h2[^>]*>(.*?)</h2>(.*?)</section>', t, re.S):
            sid, titre, corps = m.group(1), texte(m.group(2)), m.group(3)
            if sid in IGNORER_SECTIONS or (rel.startswith("categories/") and sid != "top"):
                continue
            items = re.findall(r'<span class="(?:cl|top)-rang">(\d+)</span>\s*<a class="(?:cl|top)-lien" '
                               r'href="(?:\.\./)?fiches/([^"]+)\.html"', corps)
            if not items:
                continue
            src = re.search(r'<p class="(?:cl-chapo|top-note)">(.*?)</p>', corps, re.S)
            source = ""
            if src:
                source = texte(src.group(1))
                source = re.split(r"(?<=\.)\s", source)[0]          # premiere phrase
            # Rang = position dans la liste (verifie contre le numero affiche).
            slugs = [s for _, s in sorted(items, key=lambda x: int(x[0]))]
            listes.append({"id": f"{rel}#{sid}", "url": f"{url}#{sid}", "titre": titre,
                           "source": source, "slugs": slugs})
    return listes


def exclus():
    out = set()
    try:
        out |= set(json.loads((DATA / "_complotistes.json").read_text(encoding="utf-8")))
    except Exception:
        pass
    try:
        for x in json.loads((DATA / "catalog.json").read_text(encoding="utf-8")):
            if x.get("desirs"):
                out.add(x.get("slug"))
    except Exception:
        pass
    return out


def portee(lid):
    for k, v in PORTEE.items():
        if lid.startswith(k) and (("#" in k and lid == k) or "#" not in k):
            return v
    return 1


def meilleurs(listes, interdits):
    best = {}
    for L in listes:
        for i, s in enumerate(L["slugs"], 1):
            if s in interdits or not (ROOT / "fiches" / f"{s}.html").exists():
                continue
            cle = (i, -portee(L["id"]))
            if s not in best or cle < best[s][0]:
                best[s] = (cle, L, i)
    return best


def historique(listes, aujourdhui):
    try:
        h = json.loads(HISTO.read_text(encoding="utf-8"))
    except Exception:
        h = {}
    dates = sorted(h)
    if not dates or (aujourdhui - date.fromisoformat(dates[-1])).days >= 7:
        h[aujourdhui.isoformat()] = {L["id"]: L["slugs"] for L in listes}
        dates = sorted(h)[-GARDER_SEMAINES:]
        h = {d: h[d] for d in dates}
        HISTO.write_text(json.dumps(h, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
                         encoding="utf-8")
        print(f"  historique : photo du {aujourdhui.isoformat()} ({len(dates)} semaine(s) gardée(s))")
    return h


def progression(h, lid, slug, rang_actuel, aujourdhui):
    """Comparaison avec la photo la plus ancienne de moins de 35 jours (et
    d'au moins 7 jours) : « ↑ n places depuis le … » ou nouvelle entree."""
    candidates = [d for d in sorted(h)
                  if 7 <= (aujourdhui - date.fromisoformat(d)).days <= 35 and lid in h[d]]
    if not candidates:
        return None
    d = candidates[0]
    avant = h[d][lid]
    if slug not in avant:
        return {"nouveau": True, "depuis": d}
    places = avant.index(slug) + 1 - rang_actuel
    return {"places": places, "depuis": d} if places > 0 else None


# ---------------------------------------------------------------- images
def _octets(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()
    except Exception:
        try:
            return subprocess.run(["curl", "-s", "-L", "--max-time", "20", url],
                                  capture_output=True, timeout=30).stdout
        except Exception:
            return b""


def image_rang(slug, fiche, r):
    """1200x630 : pochette a gauche, rang et nom de la liste a droite."""
    from PIL import Image, ImageDraw
    from generate_du_jour import _police, _lignes
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (8, 12, 20))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 8], fill=(232, 98, 45))
    cov = fiche.get("image") or ""
    if "mzstatic.com" in cov:
        cov = re.sub(r"/\d+x\d+bb\.(png|jpg)$", "/600x600bb.jpg", cov)
    brut = _octets(cov) if cov.startswith("https://") else b""
    x0 = 70
    try:
        c = Image.open(io.BytesIO(brut)).convert("RGB").resize((440, 440))
        im.paste(c, (x0, 95))
        tx = x0 + 440 + 60
    except Exception:
        tx = x0
    d.text((tx, 92), "CLASSEMENT MEDIACRITIC", font=_police(30), fill=(232, 98, 45))
    d.text((tx, 140), f"N° {r['rang']}", font=_police(150), fill=(238, 242, 247))
    y = 320
    for ligne in _lignes(d, fiche.get("title") or slug, _police(46), W - tx - 60, 2):
        d.text((tx, y), ligne, font=_police(46), fill=(238, 242, 247)); y += 56
    y += 10
    for ligne in _lignes(d, r["liste"], _police(30, False), W - tx - 60, 3):
        d.text((tx, y), ligne, font=_police(30, False), fill=(190, 198, 210)); y += 38
    d.text((70, H - 62), "mediacritic.fr", font=_police(30), fill=(238, 242, 247))
    IMAGES.mkdir(parents=True, exist_ok=True)
    out = IMAGES / f"{slug}.jpg"
    im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return f"assets/rangs/{slug}.jpg"


# ---------------------------------------------------------------- fiches
def patch_fiche(slug):
    """Encart d'une fiche deja ecrite (meme rendu que generate_fiches).
    L'og:image, lui, est pose par generate_fiches (rangs.og) : quand le
    podium change, on date la fiche de donnees pour qu'elle soit regeneree."""
    f = ROOT / "fiches" / f"{slug}.html"
    if not f.exists():
        return False
    t = f.read_text(encoding="utf-8")
    if rangs.DEBUT not in t:
        return False          # gabarit ancien : generate_fiches posera l'encart
    neuf = re.sub(re.escape(rangs.DEBUT) + r".*?" + re.escape(rangs.FIN),
                  lambda m: rangs.bloc(slug), t, count=1, flags=re.S)
    if neuf != t:
        f.write_text(neuf, encoding="utf-8")
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-images", action="store_true")
    a = ap.parse_args()
    aujourdhui = date.today()
    listes = lire_listes()
    h = historique(listes, aujourdhui)
    interdits = exclus()
    best = meilleurs(listes, interdits)
    try:
        sigs = json.loads(SIG_IMAGES.read_text(encoding="utf-8"))
    except Exception:
        sigs = {}
    ancien = rangs.donnees().get("rangs") or {}
    sortie = {}
    for slug, (_, L, i) in sorted(best.items()):
        r = {"rang": i, "liste": L["titre"], "url": L["url"], "source": L["source"]}
        p = progression(h, L["id"], slug, i, aujourdhui)
        if p:
            r["progression"] = p
        if i <= PODIUM:
            try:
                fiche = json.loads((DATA / "content" / f"{slug}.json").read_text(encoding="utf-8-sig"))
            except Exception:
                fiche = {"title": slug}
            sig = hashlib.sha1(json.dumps([i, L["titre"], fiche.get("title"), fiche.get("image")],
                                          ensure_ascii=False).encode()).hexdigest()[:12]
            chemin = f"assets/rangs/{slug}.jpg"
            if sigs.get(slug) == sig and (ROOT / chemin).exists():
                r["image"] = chemin
            elif not a.sans_images:
                try:
                    r["image"] = image_rang(slug, fiche, r)
                    sigs[slug] = sig
                except Exception as e:
                    print(f"  ! image {slug} : {e}")
            elif (ROOT / chemin).exists():
                r["image"] = chemin
        sortie[slug] = r
    # Images d'anciens podiums : supprimees.
    for f in IMAGES.glob("*.jpg") if IMAGES.exists() else []:
        if not (sortie.get(f.stem) or {}).get("image"):
            f.unlink()
            sigs.pop(f.stem, None)
    SIG_IMAGES.write_text(json.dumps(sigs, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    neuf = {"rangs": sortie}
    js = json.dumps(neuf, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if not rangs.SOURCE.exists() or rangs.SOURCE.read_text(encoding="utf-8") != js:
        rangs.SOURCE.write_text(js, encoding="utf-8")
    rangs.donnees(recharger=True)
    # Fiches a mettre a jour : rang nouveau, change ou disparu.
    touchees = 0
    for slug in set(sortie) | set(ancien):
        touchees += patch_fiche(slug)
        if bool((sortie.get(slug) or {}).get("image")) != bool((ancien.get(slug) or {}).get("image")):
            src = DATA / "content" / f"{slug}.json"
            if src.exists():
                os.utime(src)         # og:image a changer : generate_fiches la regenerera
    print(f"  rangs : {len(listes)} classements lus, {len(sortie)} fiches classées "
          f"({sum(1 for r in sortie.values() if r.get('image'))} images de podium), {touchees} fiche(s) mise(s) à jour")


if __name__ == "__main__":
    main()
