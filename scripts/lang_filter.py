#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filtre linguistique du catalogue MediaCritic.

Le site ne reference que du contenu francophone. Historiquement rien ne le
garantissait : le champ `language` des fiches contenait en fait le genre Apple
(`primaryGenreName`), et les podcasts etaient acceptes parce qu'ils remontaient
dans le classement FRANCAIS — ce qui ne dit rien de leur langue. D'ou des
podcasts japonais, anglais ou espagnols dans le catalogue.

Source de verite retenue : la balise <language> du flux RSS, declaree par le
producteur lui-meme. Pour YouTube (pas de flux RSS), on combine le pays de la
chaine et des marqueurs francais reels dans la description.

Regle d'or : on ne supprime jamais faute de preuve. Une langue inconnue est
conservee ; seul un code de langue explicitement non francophone exclut.
"""
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; MediaCriticBot/1.0)"}
_LANG_RE = re.compile(rb"<language>\s*([A-Za-z\-_]{2,10})\s*</language>", re.I)

# Pays ou le francais est langue officielle ou co-officielle
PAYS_FRANCOPHONES = {
    "FR", "BE", "CH", "CA", "LU", "MC", "SN", "CI", "ML", "BF", "NE", "TG",
    "BJ", "GA", "CG", "CD", "CM", "TD", "CF", "GN", "MG", "DJ", "RW", "BI",
    "KM", "SC", "VU", "HT", "MU",
}

# Marqueurs francais fiables : mots-outils qui n'existent pas en anglais.
# « podcast » et « episode » sont volontairement absents : ce sont des mots
# internationaux, et c'est precisement par eux que des chaines anglophones
# passaient le filtre.
MARQUEURS_FR = [
    " le ", " la ", " les ", " des ", " une ", " un ", " du ", " au ", " aux ",
    " est ", " sont ", " avec ", " pour ", " dans ", " sur ", " qui ", " que ",
    " nous ", " vous ", " chaque ", " tous ", " toute ", " plus ", " sans ",
    "français", "francais", "france", "bonjour", "bienvenue", "émission",
    "semaine", "chaîne", "chaine", "vidéo", "abonne",
]

# Ecritures qui excluent d'emblee (aucun contenu francophone ne s'ecrit ainsi)
_SCRIPTS_NON_LATINS = re.compile(
    r"[぀-ヿ一-鿿"      # japonais / chinois
    r"가-힯"                     # coreen
    r"Ѐ-ӿ"                     # cyrillique
    r"؀-ۿ"                     # arabe
    r"֐-׿"                     # hebreu
    r"Ͱ-Ͽ"                     # grec
    r"฀-๿ऀ-ॿ]"       # thai / devanagari
)


def est_code_francophone(code):
    """« fr », « fr-FR », « fr_CA »… -> True. None/vide -> None (inconnu)."""
    if not code:
        return None
    base = str(code).strip().lower().replace("_", "-").split("-")[0]
    if not base or base in ("?", "!"):
        return None
    return base == "fr"


def langue_du_flux(feed_url, timeout=15):
    """Langue declaree dans les premiers Ko d'un flux RSS. None si indisponible.

    On ne lit que 16 Ko : la balise <language> est dans l'en-tete du flux, et
    certains flux pesent plusieurs Mo."""
    if not feed_url:
        return None
    try:
        req = urllib.request.Request(
            feed_url, headers={**UA, "Range": "bytes=0-16383"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            head = r.read(16384)
    except Exception:
        return None
    m = _LANG_RE.search(head)
    return m.group(1).decode("ascii", "ignore").lower() if m else None


def ecriture_non_latine(texte, seuil=2):
    """True si le texte comporte assez de caracteres d'une ecriture non latine."""
    return len(_SCRIPTS_NON_LATINS.findall(str(texte or ""))) >= seuil


# Rattrapage des flux qui declarent mal leur langue (cas reels : l'audioguide
# « Pnr du Vexin Français » declare en-en, « Marketing Haute Fréquence » declare
# en). On ne se fie pas aveuglement a la declaration : un texte manifestement
# francais la contredit.
# « le » et « la » sont volontairement absents de la liste : partages avec
# l'espagnol et l'italien, ils rattrapaient a tort « El Cine en la SER ».
_MOTS_FR = [" les ", " des ", " une ", " du ", " aux ", " est ", " sont ",
            " avec ", " pour ", " dans ", " qui ", " nous ", " vous ",
            " chaque ", " sans ", " cette ", " leur ", " ainsi ", " chez ",
            " c'est ", " d'un ", " d'une ", " l'", " qu'",
            "français", "francais", "france", "bonjour", "bienvenue",
            "émission", "épisode", "chronique", "récit", "découverte"]
_MOTS_AUTRES = [" el ", " los ", " las ", " y ", " con ", " para ", " por ",
                " del ", " que ", " como ", " en la ", " de la ", " il ",
                " gli ", " che ", " sono ", " e ", " da ", " dos ", " das ",
                " uma "]


def texte_manifestement_francais(*morceaux):
    """True si le texte porte des marqueurs francais qui dominent ceux des
    autres langues latines. Sert de filet contre les flux mal declares."""
    blob = " " + " ".join(str(m or "") for m in morceaux).lower() + " "
    fr = sum(1 for m in _MOTS_FR if m in blob)
    autres = sum(1 for m in _MOTS_AUTRES if m in blob)
    return fr >= 1 and fr > autres


def podcast_francophone(item, feed_url=None):
    """Verdict pour un podcast issu d'iTunes.

    Retourne (garder: bool, code_langue: str|None).
    Un flux muet ou injoignable est conserve : on ne supprime pas sans preuve."""
    titre = f"{item.get('collectionName', '')} {item.get('artistName', '')}"
    desc = item.get("description") or item.get("shortDescription") or ""

    # Le rattrapage passe AVANT la detection d'ecriture : des podcasts francais
    # portent un sous-titre en alphabet etranger (« Apprendre le français avec
    # Ama - تعلم الفرنسية », « Les voisins du 12 bis, французько-українська »).
    # Les supprimer serait une erreur.
    if texte_manifestement_francais(titre, desc):
        return True, langue_du_flux(feed_url or item.get("feedUrl"))

    if ecriture_non_latine(titre):
        return False, None

    code = langue_du_flux(feed_url or item.get("feedUrl"))
    if est_code_francophone(code) is False:
        return False, code
    return True, code


def chaine_youtube_francophone(snippet):
    """Verdict pour une chaine YouTube (pas de flux RSS a interroger).

    Retourne (garder: bool, code_langue: str|None)."""
    titre = snippet.get("title", "")
    desc = (snippet.get("description") or "")
    if ecriture_non_latine(f"{titre} {desc}"):
        return False, None

    declaree = snippet.get("defaultLanguage") or snippet.get("country")
    code = (snippet.get("defaultLanguage") or "").lower() or None
    if est_code_francophone(code) is False:
        return False, code

    pays = (snippet.get("country") or "").upper()
    if pays and pays in PAYS_FRANCOPHONES:
        return True, code or "fr"
    if pays and pays not in PAYS_FRANCOPHONES:
        # Pays non francophone : il faut de vrais marqueurs francais
        blob = f" {titre.lower()} {desc.lower()} "
        return (sum(1 for m in MARQUEURS_FR if m in blob) >= 3), code

    # Pays non renseigne : s'appuyer sur la description
    blob = f" {titre.lower()} {desc.lower()} "
    return (sum(1 for m in MARQUEURS_FR if m in blob) >= 2), code


# ── Chaines YouTube : langue deduite des titres de videos ─────────────────────
# Les chaines n'ont pas de flux RSS declarant une langue, mais leur flux de
# videos est public et 15 titres forment un corpus bien plus fiable qu'une
# description de deux lignes.
#
# Regle d'or, identique au reste du module : on ne supprime JAMAIS faute de
# preuve. Il faut des marqueurs etrangers POSITIFS. Remi Gaillard, francais,
# publie des titres quasi sans texte (« EPILOGUE (Rémi Gaillard) 💡 ») :
# l'absence de francais ne doit pas suffire a le condamner.
_MOTS_EN = [" the ", " and ", " you ", " your ", " with ", " this ", " that ",
            " what ", " why ", " how ", " we ", " our ", " is ", " are ",
            " was ", " were ", " has ", " have ", " of ", " for ", " from ",
            " they ", " their ", " about ", " when ", " where ", " which ",
            " been ", " will ", " would ", " should ", " every ", " never ",
            " always ", " best ", " new ", " my ", " get ", " make "]


def langue_chaine_youtube(titres, description=""):
    """Verdict sur une chaine a partir des titres de ses dernieres videos.

    Retourne 'fr', 'etrangere', ou None quand rien ne permet de trancher.
    None signifie CONSERVER."""
    blob = " " + " ".join(list(titres) + [description or ""]).lower() + " "
    if ecriture_non_latine(blob, seuil=4):
        return "etrangere"

    fr = sum(1 for m in _MOTS_FR if m in blob)
    if fr >= 2:
        return "fr"

    en = sum(1 for m in _MOTS_EN if m in blob)
    autres = sum(1 for m in _MOTS_AUTRES if m in blob)
    etranger = max(en, autres)
    # marqueurs etrangers francs ET aucun marqueur francais
    if etranger >= 3 and fr == 0:
        return "etrangere"
    return None
