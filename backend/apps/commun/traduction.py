"""Traduction francais -> arabe des textes produits par le serveur (messages, libelles de documents).

Les textes francais du code servent de cles. Une cle peut contenir `{}` (une valeur variable : nom, nombre...) ;
la traduction reprend ces valeurs avec `{0}`, `{1}`... dans l'ordre d'apparition. Exemple :
    "La classe {} a deux cours en meme temps ({}) : {} et {}."
    -> "القسم {0} لديه درسان في الوقت نفسه ({1}) : {2} و{3}."

Un texte sans traduction est renvoye tel quel (jamais d'erreur) ; en mode `SUIVRE_MANQUANTS` (tests), il est consigne
dans `MANQUANTS` pour que les tests de couverture le signalent."""

import re

from .langue import langue_courante

SUIVRE_MANQUANTS = False
MANQUANTS = set()

_DIRECT = {}
_GABARITS = []     # (regex, traduction, longueur_litterale) du plus specifique au plus general
_PREFIXES = []
_PRET = False

JOURS_AR = {
    "lundi": "الاثنين", "mardi": "الثلاثاء", "mercredi": "الأربعاء", "jeudi": "الخميس",
    "vendredi": "الجمعة", "samedi": "السبت", "dimanche": "الأحد",
}
_RE_JOURS = re.compile(r"\b(" + "|".join(JOURS_AR) + r")\b", re.IGNORECASE)
_RE_PHRASES = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])")


def _preparer():
    global _PRET
    from .libelles_ar import LIBELLES_AR     # imports tardifs : les dictionnaires sont volumineux
    from .messages_ar import MESSAGES_AR, PREFIXES_AR

    for cle, valeur in {**LIBELLES_AR, **MESSAGES_AR}.items():
        if "{}" not in cle:
            _DIRECT[cle] = valeur
            continue
        morceaux = cle.split("{}")
        motif = "^" + "(.+?)".join(re.escape(m) for m in morceaux) + "$"
        _GABARITS.append((re.compile(motif, re.DOTALL), valeur, sum(len(m) for m in morceaux)))
    _GABARITS.sort(key=lambda g: -g[2])
    _PREFIXES.extend(sorted(PREFIXES_AR.items(), key=lambda kv: -len(kv[0])))
    _PRET = True


def _jours(texte):
    return _RE_JOURS.sub(lambda m: JOURS_AR[m.group(1).lower()], texte)


def _traduire_ar(texte):
    if texte in _DIRECT:
        return _DIRECT[texte]
    if " ; " in texte:
        return " ؛ ".join(_traduire_ar(partie) for partie in texte.split(" ; "))
    for motif, valeur, _ in _GABARITS:
        trouve = motif.match(texte)
        # Une valeur variable ne contient jamais une phrase entiere : sinon le gabarit a « avale » plusieurs messages.
        if trouve and not any(_RE_PHRASES.search(g) for g in trouve.groups()):
            return _jours(valeur.format(*[_traduire_valeur(g) for g in trouve.groups()]))
    for prefixe, valeur in _PREFIXES:
        if texte.startswith(prefixe):
            return valeur + _traduire_ar(texte[len(prefixe):])
    phrases = _RE_PHRASES.split(texte)
    if len(phrases) > 1:
        return " ".join(_traduire_ar(phrase) for phrase in phrases)
    if SUIVRE_MANQUANTS:
        MANQUANTS.add(texte)
    return texte


def _traduire_valeur(valeur):
    """Valeur variable d'un gabarit : traduite si c'est un libelle connu (ex. un statut), sinon inchangee."""
    return _DIRECT.get(valeur, _jours(valeur))


def traduire(texte, langue=None):
    """Texte francais -> langue courante (ou `langue`). Le francais est renvoye tel quel."""
    if not isinstance(texte, str) or not texte.strip():
        return texte
    if (langue or langue_courante()) != "ar":
        return texte
    if not _PRET:
        _preparer()
    debut = texte[: len(texte) - len(texte.lstrip())]
    fin = texte[len(texte.rstrip()):]
    return debut + _traduire_ar(texte.strip()) + fin
