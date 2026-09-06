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
RAPPORT = ROOT / "data" / "_avis_epuises.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; MediaCriticBot/1.0)"}

RAFRAICHIR_APRES = 60   # jours avant de recollecter une fiche deja traitee
RETENTER_APRES = 30     # jours avant de retenter une fiche sans avis
MIN_AVIS = 3            # en dessous, la section ne vaut pas d'etre affichee
MAX_EXTRAITS = 3        # on cite peu : ce sont les mots d'autrui
SEUIL_BRIDAGE = 12      # vides d'affilee au-dela desquels on conclut au bridage

# La cascade : 8 boutiques x 2 tris = 16 tentatives avant de conclure a
# l'absence. Les boutiques francophones d'abord, puis GB/US/MC ou des
# auditeurs expatries laissent parfois les seuls avis existants -- verifie le
# 06/09 : « Affaires sensibles » n'a d'avis citables qu'en FR et en GB.
BOUTIQUES = ["fr", "be", "ch", "ca", "lu", "gb", "us", "mc"]
TRIS = ["mosthelpful", "mostrecent"]

# Sources ecartees, et pourquoi -- pour ne pas refaire l'essai :
#   Reddit  : l'API JSON publique renvoie HTTP 403 depuis le verrouillage de
#             2023 (teste le 06/09 sur www et old.reddit.com). Il faudrait
#             enregistrer une application et gerer OAuth.
#   Discord : rien n'est indexable publiquement, y acceder suppose d'etre dans
#             le serveur et de contredire les conditions d'utilisation.
#   4chan   : republier ce contenu sous la signature du site, sans moderation,
#             sur des milliers de pages -- le risque n'a aucun rapport avec le
#             gain.
#   Presse  : legitime, mais c'est de la critique professionnelle sous droit
#             d'auteur, pas l'avis du public. Merite sa propre section, et une
#             API de recherche qu'on n'a pas.
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


def _lire_flux(track_id, tri, timeout, pays="fr"):
    """Un tri d'une boutique Apple -> liste d'avis normalises."""
    url = ("https://itunes.apple.com/%s/rss/customerreviews/"
           "id=%s/sortby=%s/json" % (pays, track_id, tri))
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
    """Cascade de sources -> extraits reels, cites et attribues.

    On essaie 16 combinaisons boutique x tri avant de conclure a l'absence.
    Ce n'est pas de la superstition : mesure du 06/09 sur trois temoins,
      - « Affaires sensibles » ne repond qu'en FR/recent et en GB/helpful ;
      - « Hondelatte Raconte » ne repond qu'en CH/recent -- alors qu'il
        renvoyait 50 avis en FR une heure plus tot ;
      - le meme podcast donne 0 puis 45 avis selon le tri, sur la meme boutique.
    Les reponses d'Apple sont erratiques et le bridage s'applique par boutique :
    un « rien » sur une seule combinaison n'est pas une preuve d'absence.

    L'ordre va du plus probable au plus exotique, et on S'ARRETE AU PREMIER
    SUCCES : la grande majorite des fiches se resout en une ou deux requetes,
    seules les difficiles descendent la cascade.

    Renvoie (bloc, sources_tentees). `bloc` vaut None si tout a echoue --
    l'appelant enregistre alors l'epuisement, pour que l'absence soit visible
    et exploitable plutot que silencieuse.

    On ne renvoie AUCUNE distribution de notes, et c'est deliberé : voir
    l'en-tete du module.
    """
    tentees = []
    for pays in BOUTIQUES:
        for tri in TRIS:
            tentees.append("apple:%s/%s" % (pays, tri))
            avis = _lire_flux(track_id, tri, timeout, pays=pays)
            if len(avis) < MIN_AVIS:
                continue
            extraits = choisir_extraits(avis)
            if not extraits:
                continue
            return {
                "source": "apple",
                "boutique": pays,
                "tri": tri,
                "releve": date.today().isoformat(),
                "extraits": extraits,
            }, tentees
    return None, tentees


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

    candidats = []
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
        apple = (d.get("platforms") or {}).get("apple") or {}
        tid = apple.get("trackId")
        if not tid:
            continue
        # Un podcast sans note Apple n'a aucun avis a citer : l'interroger
        # gaspille une requete. 1 618 fiches sur 7 215 sont dans ce cas, et
        # 2 659 ont moins de 3 notes -- soit plus d'un tiers du budget jete.
        if (apple.get("ratingCount") or 0) < MIN_AVIS:
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
        candidats.append((apple.get("ratingCount") or 0, slug, int(tid),
                          Path(f), d))

    # LES PLUS ECOUTES D'ABORD, et c'est le point decisif. La premiere version
    # parcourait `data/content/` par ordre alphabetique : elle a depense ses
    # 300 premieres requetes sur « 1&1 Font Casts », « 1/3 lieu »... des
    # podcasts a zero avis. Resultat mesure le 06/09 : 13 fiches pourvues sur
    # 300 tentatives, soit 4,3 %, alors que le taux atteint 85 % sur les fiches
    # populaires. L'ordre alphabetique servait aussi les fiches que personne ne
    # consulte avant celles qui sont en premiere page.
    candidats.sort(key=lambda c: -c[0])

    cibles, fiches = [], {}
    for _, slug, tid, path, d in candidats[:limit]:
        cibles.append((slug, tid))
        fiches[slug] = (path, d)

    if not cibles:
        if verbose:
            print("  avis publics : rien a collecter")
        return 0

    if verbose:
        print("  avis publics : %d fiche(s) a traiter" % len(cibles))

    remplies = vides = 0
    vides_daffilee = 0
    bride = False
    # Apple bride SILENCIEUSEMENT : HTTP 200, flux valide, zero avis -- pour des
    # podcasts qui en renvoyaient cinquante une heure plus tot. Sans coupe-circuit,
    # une seance bridee marque des centaines de fiches « sans avis » et
    # `RETENTER_APRES` les gele 30 jours : on inscrirait une panne reseau comme
    # une verite sur le contenu. Constate le 06/09 en mesurant les sources.
    epuisees = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(avis_apple, tid): slug for slug, tid in cibles}
        for fut in as_completed(futs):
            slug = futs[fut]
            bloc, tentees = fut.result()
            path, d = fiches[slug]
            if bloc:
                remplies += 1
                vides_daffilee = 0
                etat[slug] = "ok:" + aujourd_hui.isoformat()
                if not dry_run:
                    d["avis_publics"] = bloc
                    path.write_text(
                        json.dumps(d, ensure_ascii=False, indent=2),
                        encoding="utf-8")
                continue
            vides += 1
            vides_daffilee += 1
            if vides_daffilee >= SEUIL_BRIDAGE:
                bride = True
            if bride:
                # On ne conclut RIEN : la fiche reste vierge dans l'etat et
                # repassera a la prochaine seance. Un bridage n'est pas une
                # absence d'avis.
                continue
            etat[slug] = aujourd_hui.isoformat()
            # Epuisement enregistre SUR LA FICHE : les 16 sources ont ete
            # essayees et n'ont rien donne. C'est une information exploitable
            # -- elle alimente data/_avis_epuises.json, d'ou l'utilisateur peut
            # partir chercher une alternative, au lieu de deviner quelles fiches
            # sont muettes parmi huit mille.
            epuisees.append({
                "slug": slug,
                "titre": d.get("title"),
                "notes_apple": ((d.get("platforms") or {}).get("apple")
                                or {}).get("ratingCount") or 0,
                "fiche": "fiches/%s.html" % slug,
            })
            if not dry_run:
                d["avis_publics"] = {
                    "epuise": True,
                    "releve": aujourd_hui.isoformat(),
                    "sources_tentees": tentees,
                }
                path.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    if not dry_run:
        ETAT.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")
        # Rapport cumulatif des fiches epuisees : la liste de travail de
        # l'utilisateur pour aller chercher un avis ailleurs a la main.
        if epuisees:
            ancien = []
            if RAPPORT.exists():
                try:
                    ancien = json.loads(RAPPORT.read_text(encoding="utf-8")).get(
                        "fiches", [])
                except Exception:
                    ancien = []
            connus = {f.get("slug") for f in ancien}
            fusion = ancien + [e for e in epuisees if e["slug"] not in connus]
            fusion.sort(key=lambda f: -(f.get("notes_apple") or 0))
            RAPPORT.write_text(json.dumps(
                {"maj": aujourd_hui.isoformat(),
                 "total": len(fusion),
                 "sources_essayees_par_fiche": len(BOUTIQUES) * len(TRIS),
                 "fiches": fusion}, ensure_ascii=False, indent=2),
                encoding="utf-8")

    if verbose:
        suffixe = " (simulation)" if dry_run else ""
        print("  avis publics : %d collecte(s), %d sans avis exploitable%s"
              % (remplies, vides, suffixe))
        if bride:
            print("  avis publics : ! source bridee (%d vides d'affilee) — "
                  "seance ecourtee, aucune fiche marquee en echec"
                  % SEUIL_BRIDAGE)
        if epuisees:
            print("  avis publics : %d fiche(s) epuisee(s) apres %d sources — "
                  "voir data/_avis_epuises.json"
                  % (len(epuisees), len(BOUTIQUES) * len(TRIS)))
    return remplies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    enrich(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
