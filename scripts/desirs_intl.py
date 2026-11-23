#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
« Desire & intimacy » dans les langues du catalogue international
(demande de l'utilisateur, 23/11/2026 : « une section sensuel dans chaque
pays et chaque langue, c'est ca qui marche »).

Meme esprit que scripts/desirs.py (francais), qui reste la reference pour le
catalogue francophone :
  - sections : « fictions » (recits / histoires erotiques audio), « sexualite »
    (sexualite, couple, desir), « tantra » ;
  - JAMAIS rien qui touche aux mineurs, a l'inceste ni aux violences
    sexuelles : un seul mot de EXCLU dans le titre OU la description suffit a
    ecarter le contenu, quelle que soit la langue ;
  - un mot seul ne suffit pas : genre Apple « Sexualite » (1516), ou titre
    explicite, ou deux indices dans la description.
"""
import re
import unicodedata

GENRE_SEXUALITE = 1516

# Recherches iTunes par langue (pays, termes).
RECHERCHES = {
    "en": [("us", "erotic audio stories"), ("us", "erotic stories"), ("us", "sex podcast"),
           ("us", "sexuality podcast"), ("gb", "erotic stories"), ("gb", "sex and relationships"),
           ("au", "sex podcast"), ("ca", "erotic audio"), ("us", "tantra"), ("us", "sensual stories")],
    "es": [("es", "relatos eroticos"), ("mx", "relatos eroticos"), ("es", "sexualidad"),
           ("mx", "sexo podcast"), ("ar", "sexualidad"), ("es", "historias eroticas"), ("es", "tantra")],
    "de": [("de", "erotische geschichten"), ("de", "erotik hörspiel"), ("de", "sexualität"),
           ("de", "sex podcast"), ("at", "erotik"), ("ch", "sexualität"), ("de", "tantra")],
    "it": [("it", "racconti erotici"), ("it", "sessualità"), ("it", "sesso podcast"),
           ("it", "erotico"), ("it", "tantra")],
    "pt": [("br", "contos eroticos"), ("br", "sexualidade"), ("br", "sexo podcast"),
           ("pt", "contos eroticos"), ("pt", "sexualidade"), ("br", "tantra")],
}
QUOTAS = {"en": 300, "es": 150, "de": 150, "it": 150, "pt": 150}


def _n(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# Mineurs, inceste, non-consentement, dans les cinq langues (texte sans accents).
EXCLU = re.compile(
    r"\b(teen|teens|teenage|kid|kids|child|children|minor|minors|underage|school ?girl|"
    r"incest|rape|raped|non[- ]?consent|step ?(sister|brother|mom|mother|dad|father|daughter|son)|"
    r"daddy|ddlg|lolita|nino|nina|ninos|ninas|menor|menores|adolescente|adolescentes|colegiala|"
    r"incesto|violacion|hermanastra|hermanastro|kinder|schuler|schulerin|minderjahrig|"
    r"inzest|vergewaltigung|stiefschwester|stiefbruder|stiefmutter|stiefvater|bambin[oaie]|"
    r"minorenn[ie]|ragazzin[aeio]|stupro|sorellastra|fratellastro|crianca|criancas|"
    r"menor de idade|estupro|enteada|enteado|meia[- ]irma)\b")
FICTION = re.compile(
    r"\b(erotic(a)? (audio|stories|story|fiction|tales)|audio porn|erotica|"
    r"relatos? eroticos?|historias eroticas|cuentos eroticos|erotische (geschichten|horspiel|horspiele)|"
    r"erotik ?(horspiel|geschichten)|horspiel|racconti erotici|racconto erotico|audio racconti|"
    r"contos? eroticos?|historias eroticas|fantasy stories|sensual stories|fantasien)\b")
# Racines (sexo, sexy, sexuales, sexuell, sessuale, erotismo, porno…).
FORT = re.compile(r"\b(sex\w*|erot\w*|porn\w*|kink\w*|bdsm|orgasm\w*|sessual\w*|sesso|tantr\w*|libid\w*|"
                  r"intimit\w*|lust|prazer|placer|piacere)\b")
# Arbitrages a la main (relecture du 23/11/2026) : hors sujet malgre le
# genre Apple « Sexualite ».
EXCLURE_TITRES = {"todas as letras", "liebe leben - der podcast", "la famiglia giusta", "i hate james dobson",
                  "einschlafen mit ole augenschliesser", "mensch mit wert - der podcast",
                  "momentos con luis rodriguez", "conversa na mare"}
TANTRA = re.compile(r"\btantr(a|ic|ico|ique)\b")


def section(titre, description, genre_ids):
    """'fictions' | 'sexualite' | 'tantra' | None."""
    t, d = _n(titre), _n(description)
    if t.strip() in EXCLURE_TITRES or EXCLU.search(t) or EXCLU.search(d):
        return None
    genre = GENRE_SEXUALITE in {int(g) for g in (genre_ids or []) if str(g).isdigit()}
    forts = set(FORT.findall(d))
    # Le genre Apple seul ne suffit pas (23/11 : podcast de sommeil, emission
    # sur l'avortement, radio de nuit y etaient classes) : il faut un mot du
    # theme. Sans le genre : titre explicite ou deux indices.
    if not ((genre and (FORT.search(t) or forts)) or FORT.search(t) or FICTION.search(t) or len(forts) >= 2):
        return None
    if FICTION.search(t) or FICTION.search(d):
        return "fictions"
    if TANTRA.search(t) or TANTRA.search(d):
        return "tantra"
    return "sexualite"
