#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Met a jour la fiche d'une emission a la demande : note Apple et nombre de
notes, avis d'auditeurs, abonnes YouTube, derniers episodes. Appele par
du_jour.py sur l'emission retenue, juste avant sa publication (demande de
l'utilisateur, 08/11/2026) : le podcast du jour ne doit pas afficher des
chiffres vieux de plusieurs semaines.

Garde-fous :
  - une source muette ou bridee N'EFFACE RIEN : Apple renvoie parfois zero avis
    pour un podcast qui en a des milliers (voir enrich_avis.py) ;
  - memes sources que les enrichisseurs : note Apple seulement, jamais celle
    d'une autre plateforme ;
  - fiche critiquee par MediaCritic : pas d'avis du public (regle
    d'enrich_avis.py et de bloc_avis : notre verdict prime).

Usage :
  python scripts/rafraichir_fiche.py slug1 slug2 ...
  python scripts/rafraichir_fiche.py --tous-du-jour   # tous les choix passes
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
UA_YT = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
         "Accept-Language": "fr-FR",
         "Cookie": "SOCS=CAESEwgDEgk4NjM5OTEzODIaAmZyIAEaBgiA4P-oBg; CONSENT=YES+cb"}


def _abonnes_texte(txt):
    """« 977 k abonnés », « 1,2 M d'abonnés », « 12 300 abonnés » -> entier."""
    m = re.match(r"\s*([\d\s  .,]+)\s*(k|m|mille|million|millions)?\b", txt.lower())
    if not m or not re.search(r"\d", m.group(1)):
        return None
    brut = re.sub(r"[\s  ]", "", m.group(1))
    unite = m.group(2) or ""
    mult = 1_000 if unite in ("k", "mille") else 1_000_000 if unite in ("m", "million", "millions") else 1
    if mult == 1:
        brut = brut.replace(",", "").replace(".", "")
    try:
        return int(float(brut.replace(",", ".")) * mult)
    except ValueError:
        return None


def stats_youtube(channel_id):
    """Abonnes, vues et videos : API si la cle est la, sinon page de la chaine."""
    cle = os.environ.get("YOUTUBE_API_KEY")
    if cle:
        try:
            url = ("https://www.googleapis.com/youtube/v3/channels?part=statistics&id="
                   + urllib.parse.quote(channel_id) + "&key=" + urllib.parse.quote(cle))
            with urllib.request.urlopen(url, timeout=15) as r:
                st = json.loads(r.read().decode("utf-8"))["items"][0]["statistics"]
            return {"subscribers": int(st["subscriberCount"]), "totalViews": int(st["viewCount"]),
                    "videoCount": int(st["videoCount"])}
        except Exception:
            pass                       # quota depasse : on tente la page
    try:
        req = urllib.request.Request(f"https://www.youtube.com/channel/{channel_id}/about", headers=UA_YT)
        with urllib.request.urlopen(req, timeout=20) as r:
            x = r.read(3_000_000).decode("utf-8", "replace")
    except Exception:
        return {}
    out = {}
    # La forme « chaine simple » est celle de la chaine elle-meme ; la forme
    # objet (« accessibility ») appartient aux chaines mises en avant : c'est
    # ainsi que JeanBaptisteShow s'etait retrouve avec les 67 100 abonnes d'une
    # autre chaine.
    m = re.search(r'"subscriberCountText":"([^"]+)"', x)
    if m and _abonnes_texte(m.group(1)):
        out["subscribers"] = _abonnes_texte(m.group(1))
    m = re.search(r'"viewCountText":"([\d\s  .,]+)', x)
    if m:
        out["totalViews"] = int(re.sub(r"\D", "", m.group(1)))
    m = re.search(r'"videoCountText":"([\d\s  .,]+)', x)
    if m:
        out["videoCount"] = int(re.sub(r"\D", "", m.group(1)))
    return out


def rafraichir(slug, ecrire=True):
    """Met a jour la fiche ; renvoie {champ: (avant, apres)} des changements."""
    from collect_data import fetch_apple_rating_page
    from enrich_avis import avis_apple
    from enrich_episodes import episodes_podcast, episodes_youtube

    p = DATA / "content" / f"{slug}.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    pf = d.setdefault("platforms", {})
    faits = {}

    def poser(cible, champ, valeur, nom=None):
        if valeur is not None and cible.get(champ) != valeur:
            faits[nom or champ] = (cible.get(champ), valeur)
            cible[champ] = valeur

    apple = pf.get("apple") or {}
    tid = apple.get("trackId")
    if tid:
        note, nb = fetch_apple_rating_page(tid)
        poser(apple, "rating", note)
        poser(apple, "ratingCount", nb)
        if not d.get("mediacritic"):
            bloc, _ = avis_apple(int(tid), timeout=10)
            if bloc:                    # rien trouve : on garde l'existant
                anciens = (d.get("avis_publics") or {}).get("extraits")
                d["avis_publics"] = bloc
                if bloc["extraits"] != anciens:
                    faits["avis"] = (len(anciens or []), len(bloc["extraits"]))

    yt = pf.get("youtube") or {}
    cid = yt.get("channelId")
    if cid:
        for champ, val in stats_youtube(cid).items():
            poser(yt, champ, val)

    eps, derniere, freq = None, None, None
    try:
        if d.get("type") == "youtube" and cid:
            eps, derniere, freq = episodes_youtube(cid)
        else:
            feeds_p = DATA / "_feed_urls.json"
            feeds = json.loads(feeds_p.read_text(encoding="utf-8")) if feeds_p.exists() else {}
            if feeds.get(slug):
                eps, derniere, freq = episodes_podcast(feeds[slug])
    except Exception as e:
        print(f"  ! épisodes de {slug} : {e}")
    if eps:
        poser(d, "episodes_recents", eps, "episodes")
        poser(d, "derniere_activite", derniere)
        poser(d, "frequence_jours", freq)

    if ecrire and faits:
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return faits


def main():
    args = sys.argv[1:]
    if args == ["--tous-du-jour"]:
        hist = json.loads((DATA / "du_jour.json").read_text(encoding="utf-8"))["historique"]
        args = list(dict.fromkeys(h["slug"] for h in hist))
    for slug in args:
        faits = rafraichir(slug)
        resume = {k: v for k, v in faits.items() if k not in ("episodes",)}
        print(f"{slug} : {resume or 'chiffres inchangés'}" + (" + épisodes" if "episodes" in faits else ""))


if __name__ == "__main__":
    main()
