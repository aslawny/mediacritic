#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detection automatique des medias complotistes (demande de l'utilisateur,
16/11/2026 : « que cela soit fait automatiquement quand une nouvelle fiche
est creee »). Tourne chaque nuit dans enrich.yml AVANT generate_fiches, et
dans REGENERATEURS de publish_episode.py.

Une fiche detectee recoit le champ `avertissement` (« Note de MediaCritic »,
rendu par generate_fiches.bloc_avertissement) avec, pour preuve, DEUX de ses
propres titres recents, cites et dates. Consequences, toutes automatiques :
plus de label « independant » (independance.py lit data/_complotistes.json),
plus de badge MediaCritic, jamais podcast du jour (du_jour.py lit le meme
fichier). La fiche reste dans l'annuaire et indexee.

Prudence, parce qu'un faux positif accuse a tort. SCORE sur les titres
recents et la description : marqueur FORT = 2 (QAnon, plandemie, grand
reset, grand remplacement, HAARP, medias complotistes deja connus...),
MOYEN = 1 (Soros, mondialistes, Big Pharma, etat profond, reinformation...).
Seuil SEUIL = 4, et au moins UN titre-preuve a citer. Calibre le 16/11/2026
sur les ~9 900 fiches : 5 des 8 cas connus, aucun faux positif. Retires a
l'essai car trompeurs : « vaccin » seul (Savoir en sante), franc-maconnerie
(podcasts maconniques), « OMS » (attrapait « 1000 nOMS »), « elites ».
Score 2-3 : liste « a verifier » dans le journal, rien d'ecrit.
  - pas « Kraken » seul : plateforme crypto ; pas de mot ambigu ;
  - jamais une emission qui demonte les complots (description), un grand
    media, ni une emission critiquee par MediaCritic ;
  - `PAS_COMPLOTISTE` : liste des faux positifs signales, a tenir a jour ;
  - un avertissement ecrit a la main (sans "auto") n'est jamais touche.

Usage :
  python scripts/detect_complot.py            # applique
  python scripts/detect_complot.py --dry-run  # liste sans ecrire
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data" / "content"
LISTE = ROOT / "data" / "_complotistes.json"

FORT = re.compile(
    r"qanon|op[ée]ration q\b|ph[ée]nom[èe]ne q\b|pland[ée]mie|grand reset|great reset"
    r"|g[ée]nocide vaccinal|chemtrail|terre plate|grand remplacement|lib[ée]ration du kraken"
    r"|haarp|d[ée]qodeurs|g[ée]opolitique profonde|babel ?tv|tocsin|silvano trotta"
    r"|cr[èe]vec(?:oe|œ)ur|casasnovas|alain soral|\bertv\b|r[ée]info ?covid|bonsens"
    r"|m[ée]dia en 4-4-2|kla\.tv|ondes scalaires", re.I)
MOYEN = re.compile(
    r"\bsoros\b|mondialist|big pharma|la caste\b|arn messager|illuminati|grand r[ée]veil"
    r"|nouvel ordre mondial|deep state|[ée]tat profond|pouvoir profond|r[ée]information"
    r"|sans censure|m[ée]dias? mainstream|dissidence|bill gates|davos|macabre pacte"
    r"|vaccins? (?:tue|mortel|danger)", re.I)
SEUIL = 4
DEMONTE = re.compile(
    r"z[ée]t[ée]ti|esprit critique|debunk|fact.?check|d[ée]sinformation|vrai du (?:faux|fake)"
    r"|sceptic|sceptiq|pens[ée]e critique|d[ée]construi|explore les th[ée]ories"
    r"|comprendre (?:les|le) complot|biais cognitif", re.I)
GRANDS_MEDIAS = re.compile(
    r"radio france|france culture|france inter|franceinfo|france info|arte\b|\brfi\b|\brtl\b"
    r"|europe ?1|le monde|lib[ée]ration|le figaro|l.express|le point|slate|binge audio"
    r"|louie media|nouvelles [ée]coutes|rtbf|rts\b|radio.canada|ici premi[èe]re|bfm|lci"
    r"|france 24|france t[ée]l[ée]visions|konbini|brut\b|mediapart|l.obs\b|t[ée]l[ée]rama", re.I)
PAS_COMPLOTISTE = set()   # faux positifs signales : slugs a ne jamais marquer

MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre")


def date_fr(iso):
    try:
        d = date.fromisoformat(iso[:10])
        return f"{d.day} {MOIS[d.month - 1]} {d.year}"
    except Exception:
        return iso or ""


def _points(texte):
    return (2 * len({m.lower() for m in FORT.findall(texte)})
            + len({m.lower() for m in MOYEN.findall(texte)}))


def score(d):
    """(score, preuves triees) ; 0 pour les fiches jamais a marquer."""
    if d.get("mediacritic") or d.get("slug") in PAS_COMPLOTISTE:
        return 0, []
    desc = d.get("description") or ""
    if DEMONTE.search(desc) or GRANDS_MEDIAS.search(f"{d.get('author') or ''} {d.get('title') or ''}"):
        return 0, []
    s, preuves, vus = _points(desc), [], set()
    for e in d.get("episodes_recents") or []:
        t = (e.get("titre") or "").strip()
        if not t or t.lower() in vus:
            continue
        vus.add(t.lower())
        p = _points(t)
        if p:
            s += p
            preuves.append((p, t, e.get("date") or ""))
    return s, sorted(preuves, key=lambda x: -x[0])


def analyser(d):
    """Avertissement a poser, ou None."""
    if d.get("avertissement"):
        return None
    s, preuves = score(d)
    if s < SEUIL or not preuves:
        return None
    return {"auto": True, "detecte_le": date.today().isoformat(), "score": s,
            "exemples": [{"titre": t, "date": date_fr(dt)} for _, t, dt in preuves[:2]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    marques, nouveaux = [], []
    for f in sorted(DATA.glob("*.json")):
        try:
            raw = f.read_text(encoding="utf-8-sig")
            d = json.loads(raw)
        except Exception:
            continue
        av = analyser(d)
        if not av and not d.get("avertissement"):
            s, _ = score(d)
            if 2 <= s < SEUIL:
                print(f"  ? à vérifier (score {s}) : {d.get('slug')} ({d.get('title')})")
        if av:
            nouveaux.append((d["slug"], d.get("title"), [x["titre"] for x in av["exemples"]]))
            if not a.dry_run:
                d["avertissement"] = av
                f.write_text(json.dumps(d, ensure_ascii=False, indent=2 if "\n  \"" in raw else None),
                             encoding="utf-8")
        if d.get("avertissement") or av:
            marques.append(d["slug"])
    for slug, titre, ex in nouveaux:
        print(f"  ⚠️ nouveau : {slug} ({titre}) — {ex}")
    print(f"  complotistes : {len(marques)} fiche(s), dont {len(nouveaux)} nouvelle(s)"
          + (" (simulation)" if a.dry_run else ""))
    if not a.dry_run:
        contenu = json.dumps(sorted(marques), ensure_ascii=False, indent=0)
        if not LISTE.exists() or LISTE.read_text(encoding="utf-8") != contenu:
            LISTE.write_text(contenu, encoding="utf-8")


if __name__ == "__main__":
    main()
