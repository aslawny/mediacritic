#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimise les images locales de assets/ (Core Web Vitals).

Contexte : logo.png pesait 175 Ko et etait servi comme favicon sur les 8 145
pages du site ; ep31-bouletcorp.png et ep29-lequipe.png pesaient 2,9 et 2,7 Mo
alors qu'elles s'affichent en vignette sur la page d'accueil et le palmares.

Deux regles de prudence :
- **on ne change jamais de format**. Ces fichiers servent d'og:image, de
  twitter:image, de favicon, d'apple-touch-icon et de logo JSON-LD : le WebP
  n'est pas gere de facon fiable par les apercus sociaux.
- **on n'ecrit que si on gagne**. Certaines images sont deja optimales ; les
  recompresser les alourdirait (quelle-histoire.png : +13 %).

Les covers du catalogue ne sont pas concernees : elles sont hebergees par
Apple, Spotify et YouTube.

Usage :
  python scripts/optimise_assets.py --dry-run
  python scripts/optimise_assets.py
"""
import argparse, io, sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow requis : python -m pip install --user Pillow")

ROOT = Path(__file__).parent.parent
ASSETS = ROOT / "assets"
COTE_MAX = 1200        # aucune image du site ne s'affiche plus grand
COTE_LOGO = 512        # favicon / apple-touch-icon / logo JSON-LD (min 112 px)
LOGOS = {"logo.png", "lequipe-logo.png"}
GAIN_MINI = 5          # en dessous, on ne reecrit pas

# Budget de poids. Une image deja dans les clous n'est PAS retouchee : la
# quantification de palette est destructrice, la relancer a chaque execution
# degraderait un peu plus les images a chaque fois. Le script doit pouvoir
# tourner cent fois sans rien abimer.
BUDGET = 320 * 1024
BUDGET_LOGO = 40 * 1024


def conforme(p):
    """L'image respecte-t-elle deja dimensions ET poids ?"""
    cote = COTE_LOGO if p.name in LOGOS else COTE_MAX
    budget = BUDGET_LOGO if p.name in LOGOS else BUDGET
    if p.stat().st_size > budget:
        return False
    try:
        with Image.open(p) as im:
            return max(im.size) <= cote
    except Exception:
        return False


def optimiser(p):
    """Retourne (octets optimises, dimensions) sans ecrire."""
    im = Image.open(p)
    w, h = im.size
    cote = COTE_LOGO if p.name in LOGOS else COTE_MAX
    if max(w, h) > cote:
        r = cote / max(w, h)
        im = im.resize((round(w * r), round(h * r)), Image.LANCZOS)

    buf = io.BytesIO()
    if p.suffix.lower() == ".png":
        im2 = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
        im2 = im2.convert("P", palette=Image.ADAPTIVE, colors=256)
        im2.save(buf, "PNG", optimize=True)
    else:
        im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return buf.getvalue(), im.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    avant_total = apres_total = 0
    touches = 0
    for p in sorted(ASSETS.glob("*")):
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        avant = p.stat().st_size
        if conforme(p):
            avant_total += avant
            apres_total += avant
            print(f"  {p.name:24} {avant/1024:7.0f} Ko  conforme, non retouchee")
            continue
        try:
            data, taille = optimiser(p)
        except Exception as e:
            print(f"  {p.name:24} ignore ({e})")
            continue
        gain = 100 - len(data) * 100 / avant
        avant_total += avant
        if gain < GAIN_MINI:
            apres_total += avant
            print(f"  {p.name:24} {avant/1024:7.0f} Ko  deja optimal ({gain:.0f} %)")
            continue
        apres_total += len(data)
        touches += 1
        print(f"  {p.name:24} {avant/1024:7.0f} Ko -> {len(data)/1024:6.0f} Ko"
              f"  ({gain:3.0f} % de moins, {taille[0]}x{taille[1]})")
        if not args.dry_run:
            p.write_bytes(data)

    verbe = "seraient optimisees" if args.dry_run else "optimisees"
    print(f"\n  {touches} image(s) {verbe}")
    print(f"  total assets : {avant_total/1024:.0f} Ko -> {apres_total/1024:.0f} Ko"
          f" ({100 - apres_total*100/max(1, avant_total):.0f} % de moins)")


if __name__ == "__main__":
    main()
