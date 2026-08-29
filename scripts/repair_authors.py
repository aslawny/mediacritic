#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repare le champ `author` des fiches analysees par MediaCritic.

Le probleme : build_mediacritic_entries() (collect_data.py) cree une fiche
avec `"author": "MediaCritic"` comme valeur de depart. Comme load_existing()
renvoie ensuite la fiche telle quelle, la valeur de depart n'est jamais
corrigee -- elle est figee pour toujours. Resultat : 24 fiches attribuaient
Floodcast, Fin du Game ou L'After Foot a MediaCritic, sur leur fiche, dans
les classements et dans le comparateur. Attribuer le travail de quelqu'un
d'autre a soi-meme est une erreur qu'on ne peut pas laisser passer.

Le vrai auteur vient d'une source qui fait autorite, jamais d'une devinette :
  1. Apple    artistName, via lookup sur le trackId
  2. YouTube  titre de la chaine, via l'API
Si aucune source ne repond, la fiche est laissee telle quelle et signalee.
On ne remplace pas une valeur fausse par une valeur inventee.

Usage : python scripts/repair_authors.py [--dry-run]
        YOUTUBE_API_KEY est optionnel (18 fiches sur 24 se resolvent par Apple).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONTENT = ROOT / "data" / "content"
PLACEHOLDER = "MediaCritic"
UA = "MediaCritic/1.0 (+https://www.mediacritic.fr)"


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def auteur_apple(track_id):
    try:
        d = _get(f"https://itunes.apple.com/lookup?country=fr&id={track_id}")
        return ((d.get("results") or [{}])[0].get("artistName") or "").strip() or None
    except Exception:
        return None


def auteur_youtube(channel_id, cle):
    if not cle:
        return None
    try:
        d = _get("https://www.googleapis.com/youtube/v3/channels?part=snippet"
                 f"&id={urllib.parse.quote(channel_id)}&key={cle}")
        items = d.get("items") or []
        return ((items[0].get("snippet") or {}).get("title") or "").strip() or None if items else None
    except Exception:
        return None


def vrai_auteur(fiche, cle_yt=None):
    p = fiche.get("platforms") or {}
    tid = (p.get("apple") or {}).get("trackId")
    if tid:
        a = auteur_apple(tid)
        if a:
            return a, "apple"
    cid = (p.get("youtube") or {}).get("channelId")
    if cid:
        a = auteur_youtube(cid, cle_yt)
        if a:
            return a, "youtube"
    return None, None


def main():
    sec = "--dry-run" in sys.argv
    cle_yt = os.environ.get("YOUTUBE_API_KEY")
    corriges, echecs = [], []

    for f in sorted(CONTENT.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if (d.get("author") or "").strip() != PLACEHOLDER:
            continue
        auteur, source = vrai_auteur(d, cle_yt)
        if not auteur or auteur == PLACEHOLDER:
            echecs.append(d["slug"])
            continue
        corriges.append((d["slug"], auteur, source))
        if not sec:
            d["author"] = auteur
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.25)   # on reste poli avec les APIs publiques

    for slug, auteur, source in corriges:
        print(f"  {slug:38} -> {auteur}   ({source})")
    print(f"\n{len(corriges)} fiche(s) corrigee(s)" + ("  [essai a blanc]" if sec else ""))
    if echecs:
        print(f"{len(echecs)} sans source fiable, laissee(s) telle(s) quelle(s) : "
              + ", ".join(echecs))


if __name__ == "__main__":
    main()
