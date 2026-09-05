#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collecte les avis publics reels des auditeurs, au fil de l'eau.

Objectif : donner a chaque fiche d'annuaire une section « ce qu'en pense le
public » qui repose sur des avis REELS, cites et attribues -- jamais sur un
texte redige a partir d'eux.

Pourquoi ce choix : le garde-fou du projet interdit de fabriquer des donnees
pour remplir une section. Faire rediger une synthese par un modele produirait
du texte invérifiable, genere a l'echelle sur des milliers de pages -- ce que
Google sanctionne et ce que le skill interdit. Le flux d'avis clients d'Apple
renvoie jusqu'a 50 avis reels par podcast (note, auteur, titre, texte) : il n'y
a donc rien a inventer.

Ce qui est EXCLU :
  - les fiches analysees par MediaCritic : elles portent deja notre verdict,
    l'avis du public y ferait doublon et brouillerait la voix editoriale ;
  - les chaines YouTube : Apple n'a pas d'avis pour elles.

Honnetete de l'affichage : le flux plafonne a 50 avis. On ne publie donc
AUCUNE repartition de notes -- 50 avis ne decrivent pas un podcast qui en
compte 10 000, et sur « Affaires sensibles » (4,3 de moyenne sur 10 849 avis)
les 50 plus recents donnaient 29 notes de 1 contre 15 de 5. La moyenne
representative vient deja du lookup iTunes et s'affiche en haut de fiche ;
ce job n'ajoute que des VOIX.

Budget par execution : `--limit` fiches puis arret, pour etaler la charge sur
plusieurs nuits comme le fait enrich_descriptions.py.

Usage :
  python scripts/enrich_avis.py --dry-run
  python scripts/enrich_avis.py --limit 300
"""
import argparse, glob, html as _html, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "content"
ETAT = ROOT / "data" / "_avis_state.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; MediaCriticBot/1.0)"}

RAFRAICHIR_APRES = 60   # jours avant de recollecter une fiche deja traitee
RETENTER_APRES = 30     # jours avant de retenter une fiche sans avis
MIN_AVIS = 3            # en dessous, la section ne vaut pas d'etre affichee
MAX_EXTRAITS = 3        # on cite peu : ce sont les mots d'autrui
LONG_EXTRAIT = 280      # caracteres, au-dela on coupe proprement
MIN_EXTRAIT = 60        # un « super ! » n'apprend rien au lecteur


def nettoyer(brut):
    """Entites, balises residuelles, espaces."""
    t = re.sub(r"<[^>]+>", " ", brut or "")
    for _ in range(2):
        t = _html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def tronquer(t):
    if len(t) <= LONG_EXTRAIT:
        return t
    coupe = t[:LONG_EXTRAIT]
    point = max(coupe.rfind(". "), coupe.rfind(" ! "), coupe.rfind(" ? "))
    return (coupe[:point + 1] if point > LONG_EXTRAIT * 0.5
            else coupe.rstrip()) + "…"


def _lire_flux(track_id, tri, timeout):
    """Un tri du flux d'avis Apple -> liste d'avis normalises."""
    url = ("https://itunes.apple.com/fr/rss/customerreviews/"
           "id=%s/sortby=%s/json" % (track_id, tri))
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            flux = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return []

    entrees = (flux.get("feed") or {}).get("entry") or []
    if isinstance(entrees, dict):           # un seul avis : Apple ne liste pas
        entrees = [entrees]

    avis = []
    for e in entrees:
        # La premiere entree est parfois la fiche du podcast, pas un avis :
        # l'absence de note est le seul discriminant fiable.
        note = ((e.get("im:rating") or {}).get("label") or "").strip()
        if not note.isdigit():
            continue
        avis.append({
            "note": int(note),
            "auteur": nettoyer(((e.get("author") or {}).get("name") or {})
                               .get("label")),
            "titre": nettoyer((e.get("title") or {}).get("label")),
            "texte": nettoyer((e.get("content") or {}).get("label")),
        })
    return avis


def avis_apple(track_id, timeout=20):
    """Flux d'avis clients Apple -> extraits reels, cites et attribues.

    DEUX tris essayes, car leur disponibilite est differente et partiellement
    disjointe : mesure faite sur 4 podcasts, `mosthelpful` repond pour l'un
    quand `mostrecent` ne repond pas, et l'inverse pour deux autres. N'en
    interroger qu'un seul laisserait la moitie des fiches sans avis.
    `mosthelpful` d'abord : moins sensible aux vagues d'humeur passageres.

    On ne renvoie AUCUNE distribution de notes, et c'est deliberé. Le flux
    plafonne a 50 avis : sur « Affaires sensibles » (4,3 de moyenne sur 10 849
    avis), les 50 plus recents donnaient 29 notes de 1 contre 15 de 5. Afficher
    cette repartition sous le badge « 4,3 » aurait affiche une statistique
    fausse et visiblement contradictoire. La moyenne representative existe
    deja en haut de fiche ; ce qu'on ajoute ici, ce sont des VOIX, pas des
    chiffres.
    """
    avis = _lire_flux(track_id, "mosthelpful", timeout)
    if len(avis) < MIN_AVIS:
        avis = _lire_flux(track_id, "mostrecent", timeout)
    if len(avis) < MIN_AVIS:
        return None

    extraits = choisir_extraits(avis)
    if not extraits:
        return None

    return {
        "source": "apple",
        "releve": date.today().isoformat(),
        "extraits": extraits,
    }


def choisir_extraits(avis):
    """Choisit des avis representatifs, pas seulement les plus flatteurs.

    On prend le meilleur avis substantiel ET le plus severe s'il existe : une
    section qui ne citerait que des 5 etoiles serait de la promotion, pas de
    l'information. Un lecteur qui ne voit que des eloges cesse d'y croire.
    """
    utiles = [a for a in avis if len(a["texte"]) >= MIN_EXTRAIT]
    if not utiles:
        return []
    utiles.sort(key=lambda a: (-a["note"], -len(a["texte"])))

    choisis = [utiles[0]]                                   # le plus positif
    critiques = [a for a in utiles if a["note"] <= 3]
    if critiques:
        choisis.append(critiques[-1])                       # le plus severe
    for a in utiles:                                        # complement neutre
        if len(choisis) >= MAX_EXTRAITS:
            break
        if a not in choisis:
            choisis.append(a)

    return [{
        "note": a["note"],
        "auteur": a["auteur"] or "Auditeur Apple Podcasts",
        "titre": tronquer(a["titre"]),
        "texte": tronquer(a["texte"]),
    } for a in choisis[:MAX_EXTRAITS]]


def charger_etat():
    return json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}


def enrich(limit=300, dry_run=False, verbose=True):
    etat = charger_etat()
    aujourd_hui = date.today()
    seuil_echec = (aujourd_hui - timedelta(days=RETENTER_APRES)).isoformat()
    seuil_frais = (aujourd_hui - timedelta(days=RAFRAICHIR_APRES)).isoformat()

    cibles, fiches = [], {}
    for f in sorted(glob.glob(str(DATA / "*.json"))):
        try:
            d = json.loads(open(f, encoding="utf-8-sig").read())
        except Exception:
            continue
        slug = d.get("slug")
        if not slug:
            continue
        # Fiches analysees par MediaCritic : notre verdict prime, on n'y ajoute
        # pas l'avis du public.
        if d.get("mediacritic"):
            continue
        if d.get("type") == "youtube":
            continue
        tid = ((d.get("platforms") or {}).get("apple") or {}).get("trackId")
        if not tid:
            continue
        marque = etat.get(slug)
        if isinstance(marque, str):
            # "ok:AAAA-MM-JJ" = collecte reussie, on rafraichit apres 60 jours.
            # "AAAA-MM-JJ" seul = echec, on retente apres 30 jours.
            if marque.startswith("ok:"):
                if marque[3:] > seuil_frais:
                    continue
            elif marque > seuil_echec:
                continue
        cibles.append((slug, int(tid)))
        fiches[slug] = (Path(f), d)
        if len(cibles) >= limit:
            break

    if not cibles:
        if verbose:
            print("  avis publics : rien a collecter")
        return 0

    if verbose:
        print("  avis publics : %d fiche(s) a traiter" % len(cibles))

    remplies = vides = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(avis_apple, tid): slug for slug, tid in cibles}
        for fut in as_completed(futs):
            slug = futs[fut]
            bloc = fut.result()
            if bloc:
                remplies += 1
                etat[slug] = "ok:" + aujourd_hui.isoformat()
                if not dry_run:
                    path, d = fiches[slug]
                    d["avis_publics"] = bloc
                    path.write_text(
                        json.dumps(d, ensure_ascii=False, indent=2),
                        encoding="utf-8")
            else:
                vides += 1
                etat[slug] = aujourd_hui.isoformat()

    if not dry_run:
        ETAT.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")

    if verbose:
        suffixe = " (simulation)" if dry_run else ""
        print("  avis publics : %d collecte(s), %d sans avis exploitable%s"
              % (remplies, vides, suffixe))
    return remplies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    enrich(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
