#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enregistre chaque nuit les metriques d'audience du catalogue.

Sans historique, impossible de dire quels contenus MONTENT -- l'angle
editorial le plus interessant d'un annuaire, et celui qui fait revenir. Aucune
donnee historique n'existait : chaque nuit sans capture etait definitivement
perdue. D'ou ce script, volontairement lance tot dans la feuille de route.

Format : un fichier par mois, data/history/AAAA-MM.json
    { "slug": { "JJ": [nb_avis_apple, abonnes_youtube] } }

Seules les valeurs QUI ONT CHANGE depuis le dernier releve sont ecrites. Sur
un catalogue de 8 300 entrees dont une poignee bouge chaque jour, cela garde
les fichiers a quelques dizaines de Ko au lieu de 330 Ko par nuit.

Usage :
  python scripts/snapshot_metrics.py            # releve du jour
  python scripts/snapshot_metrics.py --dry-run
"""
import argparse, glob, json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
HIST = ROOT / "data" / "history"


def valeurs_du_jour():
    """slug -> [nb_avis, abonnes] pour tout le catalogue."""
    out = {}
    for f in glob.glob(str(ROOT / "data" / "content" / "*.json")):
        try:
            d = json.loads(open(f, encoding="utf-8-sig").read())
        except Exception:
            continue
        slug = d.get("slug")
        if not slug:
            continue
        pf = d.get("platforms") or {}
        avis = (pf.get("apple") or {}).get("ratingCount")
        subs = (pf.get("youtube") or {}).get("subscribers")
        if avis is None and subs is None:
            continue
        out[slug] = [int(avis or 0), int(subs or 0)]
    return out


def derniere_valeur(slug, avant=None):
    """Dernier releve connu pour un slug, tous mois confondus."""
    for f in sorted(HIST.glob("*.json"), reverse=True):
        try:
            mois = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        jours = mois.get(slug)
        if jours:
            j = max(jours)
            return jours[j]
    return None


def enregistrer(dry_run=False):
    HIST.mkdir(parents=True, exist_ok=True)
    aujourd_hui = date.today()
    fichier = HIST / f"{aujourd_hui:%Y-%m}.json"
    mois = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    jour = f"{aujourd_hui.day:02d}"

    # Dernier releve connu, pour n'ecrire que les variations
    connus = {}
    for f in sorted(HIST.glob("*.json")):
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for slug, jours in m.items():
            connus[slug] = jours[max(jours)]

    valeurs = valeurs_du_jour()
    ecrits = inchanges = 0
    for slug, v in valeurs.items():
        if connus.get(slug) == v:
            inchanges += 1
            continue
        mois.setdefault(slug, {})[jour] = v
        ecrits += 1

    if not dry_run and ecrits:
        fichier.write_text(json.dumps(mois, ensure_ascii=False,
                                      separators=(",", ":")), encoding="utf-8")
    suffixe = " (simulation)" if dry_run else ""
    taille = fichier.stat().st_size / 1024 if fichier.exists() else 0
    print(f"  historique : {ecrits} variation(s) enregistrée(s), "
          f"{inchanges} inchangée(s){suffixe}")
    print(f"  historique : {fichier.name} → {taille:.0f} Ko, "
          f"{len(list(HIST.glob('*.json')))} mois archivé(s)")
    return ecrits


def progression(jours=30, mini_avis=50, mini_subs=5000, top=20):
    """Plus fortes progressions relatives entre le plus ancien relevé
    disponible dans la fenêtre et le plus récent.

    Retourne [] tant que l'historique est trop court : on ne fabrique pas un
    classement à partir de données inexistantes."""
    releves = {}
    for f in sorted(HIST.glob("*.json")):
        mois = f.stem
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for slug, js in m.items():
            for j, v in js.items():
                releves.setdefault(slug, {})[f"{mois}-{j}"] = v
    if not releves:
        return []
    dates = sorted({d for v in releves.values() for d in v})
    if len(dates) < 2:
        return []
    recent, ancien = dates[-1], dates[max(0, len(dates) - jours)]
    if recent == ancien:
        return []

    out = []
    for slug, v in releves.items():
        dispo = sorted(v)
        av = next((v[d] for d in dispo if d >= ancien), None)
        ap = v[dispo[-1]]
        if not av:
            continue
        for i, seuil in ((0, mini_avis), (1, mini_subs)):
            if av[i] >= seuil and ap[i] > av[i]:
                out.append({"slug": slug, "avant": av[i], "apres": ap[i],
                            "gain": round((ap[i] - av[i]) * 100 / av[i], 1),
                            "metrique": "avis" if i == 0 else "abonnés"})
    out.sort(key=lambda x: -x["gain"])
    return out[:top]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    enregistrer(dry_run=args.dry_run)
    p = progression()
    print(f"  progressions calculables : {len(p)}"
          + ("" if p else " (historique trop court — normal au démarrage)"))
