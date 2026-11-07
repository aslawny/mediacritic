#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liste de prospection des emissions critiquees (vague 2 SEO, 07/11/2026) :
pour chacune, ses contacts OFFICIELS (comptes sociaux releves par
reseaux_emission.py, adresse de contact declaree dans son flux RSS
<itunes:email>, site officiel), un message personnalise et le code de son
badge. Fichier de travail de l'equipe, ecrit HORS du site (jamais publie).

L'equipe envoie elle-meme les messages : rien n'est envoye automatiquement.
Usage : python scripts/prospection_badges.py SORTIE.md
"""
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from badges import BASE, code_badge  # noqa: E402
from reseaux_emission import reseaux  # noqa: E402

ROOT = Path(__file__).parent.parent
NOMS = {"instagram": "Instagram", "x": "X", "tiktok": "TikTok", "facebook": "Facebook",
        "linkedin": "LinkedIn", "youtube": "YouTube", "threads": "Threads",
        "bluesky": "Bluesky", "twitch": "Twitch"}


def flux_contact(slug):
    feeds = json.loads((ROOT / "data" / "_feed_urls.json").read_text(encoding="utf-8"))
    u = feeds.get(slug)
    if not u:
        return None, None
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        tete = urllib.request.urlopen(req, timeout=20).read(150000).decode("utf-8", "replace").split("<item", 1)[0]
    except Exception:
        return None, None
    mail = re.search(r"<itunes:email>\s*([^<\s]+@[^<\s]+)\s*</itunes:email>", tete)
    site = re.search(r"<link>\s*(https?://[^<\s]+)\s*</link>", tete)
    mail = mail.group(1) if mail else None
    # Adresses-relais generees par les hebergeurs (« info+…@mg-eu.acast.com ») :
    # pas un vrai contact de l'emission.
    if mail and re.search(r"acast\.com|ausha|audiomeans|anchor\.fm|spotify|podcasters\.spotify|\+", mail, re.I):
        mail = None
    return mail, (site.group(1) if site else None)


def fiche_emission(c, page):
    slug, titre, note = c["slug"], c.get("title") or c["slug"], c["mcNote"]
    url = f"{BASE}/episodes/{page}" if page else f"{BASE}/fiches/{slug}.html"
    mail, site = flux_contact(slug) if c.get("type") != "youtube" else (None, None)
    res = reseaux(slug, c.get("type"))
    n = str(note).replace(".", ",")
    message = (f"Bonjour,\n\nNous avons consacré un épisode de MediaCritic à {titre}, avec une note de "
               f"{n}/10 : {url}\n\nMediaCritic est un annuaire et un podcast de critiques des podcasts et "
               f"chaînes YouTube francophones. Si ça vous fait plaisir, voici votre badge à afficher sur "
               f"votre site, votre page de liens ou la description de vos épisodes (code à coller) :\n\n"
               f"{code_badge(slug, titre, note, cible=url)}\n\nBelle journée,\nAlex & Lolo — MediaCritic")
    return titre, n, url, mail, site, res, message


def main():
    sortie = Path(sys.argv[1])
    revues = json.loads((ROOT / "data" / "mc_reviews.json").read_text(encoding="utf-8"))
    page_de = {v["slug"]: v.get("page") for v in revues.values() if v.get("slug")}
    cat = [c for c in json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
           if c.get("mcNote") is not None]
    cat.sort(key=lambda c: (-float(c["mcNote"]), (c.get("title") or "").lower()))
    with ThreadPoolExecutor(8) as ex:
        lignes = list(ex.map(lambda c: fiche_emission(c, page_de.get(c["slug"])), cat))
    md = ["# Badges MediaCritic — émissions critiquées à contacter", "",
          "Contacts relevés dans les sources officielles de chaque émission (page YouTube, flux, "
          "site, description). Rien n'est deviné ; une case vide = rien trouvé, à chercher à la main.",
          "Coche quand c'est envoyé : `[x]`.", ""]
    for titre, n, url, mail, site, res, message in lignes:
        md += [f"## [ ] {titre} — {n}/10", "", f"- Notre critique : {url}"]
        if mail:
            md.append(f"- E-mail déclaré dans son flux : {mail}")
        if site:
            md.append(f"- Site : {site}")
        for r, comptes in res.items():
            md.append(f"- {NOMS.get(r, r)} : " + ", ".join(f"{x['url']}" for x in comptes))
        if not (mail or site or res):
            md.append("- Aucun contact trouvé dans les sources officielles.")
        md += ["", "```text", message, "```", ""]
    sortie.write_text("\n".join(md), encoding="utf-8")
    avec = sum(1 for l in lignes if l[3] or l[4] or l[5])
    print(f"{len(lignes)} émissions, {avec} avec au moins un contact -> {sortie}")


if __name__ == "__main__":
    main()
