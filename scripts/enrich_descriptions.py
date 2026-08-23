#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remplit au fil de l'eau les descriptions manquantes des fiches du catalogue.

Constat a l'origine : 5 991 fiches sur 8 377 (71 %) avaient une description
totalement vide. Leur page affichait un titre « A propos de X » suivi de rien
-- decevant pour le visiteur, et du contenu mince a grande echelle pour Google.

Cause : collect_itunes_top_charts() ecrivait "description": "" en dur, et
aucun job ne repassait derriere. Le mode refresh du bot ne rafraichissait que
les notes Apple.

Source retenue : le flux RSS du podcast. Le lookup iTunes ne renvoie PAS de
description (verifie : 0 caractere sur tous les echantillons), seul le flux en
contient une, et elle est riche (400 a 1700 caracteres).

Budget par execution : le job traite `--limit` fiches puis s'arrete, pour
etaler la charge sur plusieurs nuits plutot que de lancer 6 000 requetes d'un
coup. Appele automatiquement en fin de chaque run du bot.

Usage :
  python scripts/enrich_descriptions.py --dry-run
  python scripts/enrich_descriptions.py --limit 400
"""
import argparse, glob, html as _html, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "content"
ETAT = ROOT / "data" / "_desc_state.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; MediaCriticBot/1.0)"}

MIN_UTILE = 40          # en dessous, la description n'apporte rien
MAX_LONGUEUR = 1200     # au-dela, on tronque proprement
RETENTER_APRES = 30     # jours avant de retenter un flux muet ou injoignable

_SUMMARY = re.compile(
    r"<itunes:summary>(.*?)</itunes:summary>|<description>(.*?)</description>",
    re.S | re.I)


def nettoyer(brut):
    """CDATA, balises, entites (parfois doublement encodees), espaces."""
    t = re.sub(r"<!\[CDATA\[|\]\]>", "", brut)
    t = re.sub(r"<br\s*/?>|</p>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    for _ in range(2):                      # &amp;amp; -> &amp; -> &
        t = _html.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    # les flux collent souvent une mention d'hebergeur en fin de description
    t = re.split(r"\s*(?:---\s*)?H[ée]berg[ée] par Acast|"
                 r"\s*Hosted on Acast|\s*Visitez acast\.com", t)[0].strip()
    if len(t) > MAX_LONGUEUR:
        coupe = t[:MAX_LONGUEUR]
        point = max(coupe.rfind(". "), coupe.rfind(" ! "), coupe.rfind(" ? "))
        t = (coupe[:point + 1] if point > MAX_LONGUEUR * 0.6 else coupe.rstrip()) + "…"
    return t


def description_du_flux(feed_url, timeout=20):
    """Premiers Ko du flux -> description du PODCAST (pas d'un episode)."""
    if not feed_url:
        return None
    try:
        req = urllib.request.Request(feed_url,
                                     headers={**UA, "Range": "bytes=0-32767"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            head = r.read(32768).decode("utf-8", "replace")
    except Exception:
        return None
    # on s'arrete au premier <item> : au-dela ce sont les episodes
    tete = head.split("<item")[0] or head
    for m in _SUMMARY.finditer(tete):
        txt = nettoyer(m.group(1) or m.group(2) or "")
        if len(txt) >= MIN_UTILE:
            return txt
    return None


def charger_etat():
    return json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}


def resoudre_feeds(cibles):
    """trackId -> feedUrl, par lots de 100 (1 appel pour 100 fiches)."""
    feeds, ids = {}, [t for _, t in cibles]
    par_id = {t: s for s, t in cibles}
    for i in range(0, len(ids), 100):
        url = ("https://itunes.apple.com/lookup?country=fr&id="
               + ",".join(str(x) for x in ids[i:i + 100]))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read().decode("utf-8", "replace"))
            for x in res.get("results", []):
                tid = x.get("collectionId") or x.get("trackId")
                if tid in par_id and x.get("feedUrl"):
                    feeds[par_id[tid]] = x["feedUrl"]
        except Exception as e:
            print(f"    lookup lot {i // 100 + 1} : {e}")
        time.sleep(0.2)
    return feeds


def enrich(limit=400, dry_run=False, verbose=True):
    etat = charger_etat()
    aujourd_hui = date.today()
    seuil = (aujourd_hui - timedelta(days=RETENTER_APRES)).isoformat()

    cibles, fiches = [], {}
    for f in sorted(glob.glob(str(DATA / "*.json"))):
        try:
            d = json.loads(open(f, encoding="utf-8-sig").read())
        except Exception:
            continue
        slug = d.get("slug")
        if not slug or len((d.get("description") or "").strip()) >= MIN_UTILE:
            continue
        marque = etat.get(slug)
        if marque == "ok" or (isinstance(marque, str) and marque > seuil):
            continue                        # deja traite, ou echec recent
        tid = ((d.get("platforms") or {}).get("apple") or {}).get("trackId")
        if tid:
            cibles.append((slug, int(tid)))
            fiches[slug] = (Path(f), d)
        if len(cibles) >= limit:
            break

    if not cibles:
        if verbose:
            print("  descriptions : rien a completer")
        return 0

    if verbose:
        print(f"  descriptions : {len(cibles)} fiche(s) a completer")
    feeds = resoudre_feeds(cibles)

    remplies = vides = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(description_du_flux, u): s for s, u in feeds.items()}
        for fut in as_completed(futs):
            slug = futs[fut]
            txt = fut.result()
            if txt:
                remplies += 1
                etat[slug] = "ok"
                if not dry_run:
                    path, d = fiches[slug]
                    d["description"] = txt
                    path.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
            else:
                vides += 1
                etat[slug] = aujourd_hui.isoformat()
    for slug, _ in cibles:                  # feedUrl introuvable
        etat.setdefault(slug, aujourd_hui.isoformat())

    if not dry_run:
        ETAT.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")

    if verbose:
        suffixe = " (simulation)" if dry_run else ""
        print(f"  descriptions : {remplies} remplie(s), "
              f"{vides} flux muet(s) ou injoignable(s){suffixe}")
        restant = sum(1 for f in glob.glob(str(DATA / "*.json"))
                      if _est_vide(f) and etat.get(Path(f).stem) != "ok")
        print(f"  descriptions : ~{restant} fiche(s) encore a traiter")
    return remplies


def _est_vide(f):
    try:
        d = json.loads(open(f, encoding="utf-8-sig").read())
    except Exception:
        return False
    return len((d.get("description") or "").strip()) < MIN_UTILE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    enrich(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
