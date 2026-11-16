#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Categorie « Desirs & intimite » (decision de l'utilisateur, 16/11/2026) :
podcasts erotiques, sensuels et sur la sexualite. Page
categories/podcasts-erotiques.html : les recherches « sex audio / audio
sexe » font ~7 % des clics Google du site, toutes sur une seule fiche.

DISCRETE : ni menu, ni accueil, ni liens croises des autres categories,
jamais podcast du jour. Acces : fiches membres (puce « Désirs & intimité »),
sitemap, annuaire.

`section(d)` decide, a partir d'une fiche ou d'une entree du catalogue :
  "fictions" : fictions et lectures erotiques (ce que vise « audio sex ») ;
  "sexualite" : sexualite, couple et desir (education, temoignages) ;
  "tantra" : tantra et intimite ;
  None : hors categorie.
Prudence : un mot seul ne suffit pas (« Philosophy is Sexy » est de la
philo, « Dans l'intimite de l'Histoire » de l'histoire). JAMAIS rien qui
touche aux enfants ni aux violences sexuelles.
"""
import re
import unicodedata


def _n(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s)


FORT = re.compile(r"erot|sexualit|\bsexe\b|\bsex\b|sexuel|sensualit|sensuel|tantra|tantriq"
                  r"|libido|orgasm|plaisir feminin|kamasutra|charnel|\bporn")
FICTION = re.compile(r"erot|histoires? (?:hot|coquine|chaude|sensuelle)|lectures? (?:erot|sensuel)"
                     r"|fictions? (?:erot|sensuel)|audio erot|\bhot stories\b|nouvelles? erot|fantasme")
FICTION_DESC = re.compile(r"(?:histoires?|recits?|lectures?|nouvelles?|fictions?|audios?|contes?)"
                          r" (?:audio )?(?:erotiques?|coquines?|sensuelles?|porno)"
                          r"|(?:audio|podcast|serie) erotique|porno audio|sexe audio|textes? erotiques?")
TANTRA = re.compile(r"tantra|tantriq")
MOYEN = re.compile(r"desir|fantasm|plaisir|intimit|\bsexo\b|sexolog")
# Dans le TITRE : sujet hors categorie. Dans la description, ces mots peuvent
# n'etre qu'un theme parmi d'autres d'une emission d'education sexuelle.
EXCLU_TITRE = re.compile(r"enfant|kids|\bado|adolescen|violences? sexuel|abus sexuel|inceste|pedo"
                         r"|harcelement|agression|\bviol\b|parentalite")
EXCLU_DESC = re.compile(r"pour (?:les )?enfants|jeune public|\bkids\b|pedocrimin|inceste")
CATS_EXCLUES = {"enfants", "famille", "jeunesse"}
# Arbitrages a la main : a completer quand un cas est signale.
INCLURE = {"le-verrou": "fictions", "les-chemins-de-desir": "fictions"}   # slug -> section
EXCLURE = {"philosophy-is-sexy", "philosophy-is-sexy-for-kids", "dans-l-intimite-de-l-histoire",
           "seroths", "un-podcast-a-soi", "proteger-son-enfant-des-violences-sexuelles",
           "la-revolution-sera-feministe", "portraits-de-femmes-en-feu",
           "sex-games-and-rock-n-roll", "decousu", "renverser-la-table",
           "la-bonne-vivance-par-julien-menielle", "romance-et-obsession",
           # 16/11/2026, relecture de la decouverte ciblee :
           "fais-pas-genre-les-metiers-du-spectacle-et-de-l-audiovisuel-n-ont-pas-de-sexe",
           "le-pouvoir-a-t-il-un-sexe", "orgasme-acoustique",
           "quand-la-sexualite-blesse", "constellation"}

NOMS = {"fictions": "Fictions & lectures érotiques",
        "sexualite": "Sexualité, couple & désir",
        "tantra": "Tantra & intimité"}


def section(d):
    slug = d.get("slug") or ""
    if slug in INCLURE:
        return INCLURE[slug]
    if slug in EXCLURE or CATS_EXCLUES & set(d.get("categories") or []):
        return None
    titre, desc = _n(d.get("title")), _n(d.get("description"))
    tout = f"{titre} {desc}"
    if EXCLU_TITRE.search(titre) or EXCLU_DESC.search(desc):
        return None
    forts = set(FORT.findall(desc))
    moyens = set(MOYEN.findall(desc))
    # Titre explicite, OU deux indices forts, OU un fort + un moyen.
    if not (FORT.search(titre) or re.search(r"\bsexo\b", titre) or len(forts) >= 2
            or (forts and moyens)):
        return None
    # Fiction : indice dans le TITRE, ou description qui annonce clairement des
    # recits / lectures erotiques (« fantasme » seul ne suffit plus : des
    # emissions de discussion etaient classees en fictions, 16/11/2026).
    if FICTION.search(titre) or FICTION_DESC.search(desc):
        return "fictions"
    if TANTRA.search(tout):
        return "tantra"
    return "sexualite"
