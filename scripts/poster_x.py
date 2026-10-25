#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publie le « podcast du jour » sur X (@MediaCriticInc), seul, chaque matin
(demande de l'utilisateur, 25/10/2026 : publication sans controle prealable,
il signale les choix qui ne vont pas).

Acces : 4 secrets GitHub crees par l'utilisateur sur developer.x.com (app en
« Read and write ») — X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN,
X_ACCESS_SECRET. Absents => etape sautee sans erreur. Ne jamais les ecrire
dans un fichier ni les afficher.

Le message porte un lien vers podcast-du-jour.html : X affiche alors la carte
avec le visuel du jour (og:image), sans televersement d'image.

Tags (« les personnes qui font le podcast ou a tenir informees ») : au plus
deux comptes, et UNIQUEMENT des comptes surs, jamais devines :
  1. COMPTES_EMISSIONS : verifies a la main (animateurs / compte officiel) ;
  2. un lien x.com / twitter.com dans la description officielle de
     l'emission ou dans l'en-tete de son flux (pas dans les episodes : ce
     sont des invites) ;
  3. COMPTES_EDITEURS : compte officiel du diffuseur (RTL, France Inter…).
Chaque compte est controle (il doit exister) avant publication. Un compte qui
« existe » n'est pas pour autant le bon : d'ou l'interdiction de deviner.

Idempotent : l'identifiant du post est garde dans data/du_jour.json (cle
« x ») ; une relance ne republie pas.

Usage :
  python scripts/poster_x.py            # publie l'entree du jour si besoin
  python scripts/poster_x.py --dry-run  # affiche le message, ne publie pas
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
BASE = "https://www.mediacritic.fr"
API = "https://api.x.com/2/tweets"
UA = {"User-Agent": "MediaCriticBot/1.0 (https://www.mediacritic.fr)"}

# Verifies a la main. Ajouter ici quand l'utilisateur signale un compte ;
# ne jamais ajouter un compte « probable ».
COMPTES_EMISSIONS = {
    "underscore": ["Micode"],
    "safepace": ["hugoclement"],
    "un-bon-moment-avec-kyan-khojandi-et-navo": ["kyankhojandi", "navo"],
    "laurent-baffie": ["laurentbaffie"],
    "floodcast": ["FloBer"],
    "le-rendez-vous-tech": ["notpatrick"],
    "trashtalk": ["trashtalk_fr"],
}
# Comptes officiels des diffuseurs, par valeur exacte du champ « author ».
COMPTES_EDITEURS = {
    "RTL": "RTLFrance", "France Inter": "franceinter", "France Culture": "franceculture",
    "France Musique": "francemusique", "franceinfo": "franceinfo", "RFI": "RFI",
    "Europe 1": "Europe1", "Europe1": "Europe1", "RMC": "RMCinfo",
    "BFM Business": "bfmbusiness", "Radio Nova": "laradionova",
    "Slate.fr Podcasts": "slatefr", "Binge Audio": "BingeAudio",
    "Louie Media": "LouieMedia", "ARTE Radio": "arteradio", "Le Monde": "lemondefr",
}
GENERIQUES = {"intent", "share", "home", "i", "hashtag", "search", "mediacriticinc", "x", "twitter"}
LIEN_X = re.compile(r"(?:twitter\.com|x\.com)/(?:#!/)?@?([A-Za-z0-9_]{2,15})(?=[\"'/?\s<)]|$)")


def compte_existe(handle):
    url = "https://publish.twitter.com/oembed?url=" + urllib.parse.quote(f"https://twitter.com/{handle}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def comptes_officiels(entree):
    slug = entree["slug"]
    cands = list(COMPTES_EMISSIONS.get(slug, []))
    fiche = DATA / "content" / f"{slug}.json"
    d = json.loads(fiche.read_text(encoding="utf-8")) if fiche.exists() else {}
    cands += LIEN_X.findall(d.get("description") or "")
    feeds = DATA / "_feed_urls.json"
    flux = json.loads(feeds.read_text(encoding="utf-8")).get(slug) if feeds.exists() else None
    if flux:
        try:
            req = urllib.request.Request(flux, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                tete = r.read(150000).decode("utf-8", "replace").split("<item", 1)[0]
            cands += LIEN_X.findall(tete)
        except Exception:
            pass
    editeur = COMPTES_EDITEURS.get((entree.get("auteur") or d.get("author") or "").strip())
    if editeur:
        cands.append(editeur)
    vus, out = set(), []
    for c in cands:
        if c.lower() in GENERIQUES or c.lower() in vus:
            continue
        vus.add(c.lower())
        if compte_existe(c):
            out.append(c)
        if len(out) >= 2:
            break
    return out


def longueur_x(texte):
    """Longueur comptee par X : URL = 23, emoji = 2."""
    t = re.sub(r"https?://\S+", "x" * 23, texte)
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in t)


def message(e, comptes):
    lien = f"{BASE}/podcast-du-jour.html?utm_source=x&utm_medium=social&utm_campaign=du-jour"
    tags = " ".join("@" + c for c in comptes)
    if e.get("mode") == "actu":
        tete = ("🔥 La chaîne du jour" if e.get("type") == "youtube" else "🔥 Le podcast du jour")
        ep = (e.get("episode") or {}).get("titre", "")
        corps = f"« {e['sujet']} » fait l'actu : {e['titre']} en parle dans « {ep} »."
    else:
        tete = "💎 La pépite du jour"
        corps = f"{e['titre']}, podcast indépendant à découvrir."
    def compose(c):
        return f"{tete} : {e['titre']}\n\n{c}" + (f"\n\n{tags}" if tags else "") + f"\n\n👉 {lien}\n#podcast"
    texte = compose(corps)
    while longueur_x(texte) > 275 and len(corps) > 40:
        corps = corps[:-12].rsplit(" ", 1)[0] + "…»" if "« " in corps else corps[:-12] + "…"
        texte = compose(corps)
    return texte


def _pct(s):
    return urllib.parse.quote(str(s), safe="~-._")


def publier(texte):
    ck, cs = os.environ["X_API_KEY"], os.environ["X_API_SECRET"]
    tk, ts = os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"]
    oauth = {"oauth_consumer_key": ck, "oauth_nonce": secrets.token_hex(16),
             "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
             "oauth_token": tk, "oauth_version": "1.0"}
    # Corps JSON : il n'entre pas dans la signature OAuth 1.0a.
    base = "&".join(["POST", _pct(API), _pct("&".join(f"{_pct(k)}={_pct(v)}"
                                                       for k, v in sorted(oauth.items())))])
    cle = f"{_pct(cs)}&{_pct(ts)}".encode()
    oauth["oauth_signature"] = base64.b64encode(hmac.new(cle, base.encode(), hashlib.sha1).digest()).decode()
    entete = "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))
    req = urllib.request.Request(API, data=json.dumps({"text": texte}).encode("utf-8"), method="POST",
                                 headers={"Authorization": entete, "Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))["data"]["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = DATA / "du_jour.json"
    if not src.exists():
        print("data/du_jour.json absent : rien à publier")
        return
    etat = json.loads(src.read_text(encoding="utf-8"))
    e = etat["historique"][0]
    if e.get("x"):
        print(f"Déjà publié sur X : {e['x'].get('id')}")
        return
    if e["date"] != datetime.now(timezone.utc).date().isoformat() and not a.dry_run:
        print(f"L'entrée du jour n'existe pas (dernière : {e['date']}) : rien à publier")
        return
    comptes = comptes_officiels(e)
    texte = message(e, comptes)
    print(f"Comptes tagués : {comptes or 'aucun compte sûr trouvé'}\n---\n{texte}\n--- ({longueur_x(texte)} car.)")
    if a.dry_run:
        return
    if not all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")):
        print("Accès X non configurés (secrets GitHub absents) : publication sautée.")
        return
    try:
        pid = publier(texte)
    except urllib.error.HTTPError as err:
        corps = err.read().decode("utf-8", "replace")[:300]
        print(f"! X a refusé la publication ({err.code}) : {corps}")
        sys.exit(1)
    e["x"] = {"id": pid, "url": f"https://x.com/MediaCriticInc/status/{pid}", "comptes": comptes}
    src.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Publié : {e['x']['url']}")


if __name__ == "__main__":
    main()
