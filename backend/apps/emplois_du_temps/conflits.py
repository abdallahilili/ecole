"""Detection des conflits d'un emploi du temps (module pur, sans base de donnees).

Contraintes OBLIGATOIRES (un emploi du temps qui en viole une n'est jamais
valide, ni publiable) : professeur / salle / classe / groupe simultanes,
professeur ou salle indisponible, horaires hors cadre ou sur une pause,
duree hors limites, capacite de salle insuffisante, professeur non affecte.
Les heures sont des minutes depuis minuit."""

from dataclasses import dataclass, field

NOMS_JOURS = {0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi", 4: "vendredi", 5: "samedi", 6: "dimanche"}


def minutes(heure):
    return heure.hour * 60 + heure.minute


def hhmm(valeur):
    return f"{valeur // 60:02d}:{valeur % 60:02d}"


@dataclass
class Sc:
    """Seance programmee (forme pure)."""

    cle: object
    classe: int
    groupe: object
    matiere: int
    professeur: int
    salle: object
    jour: int
    debut: int
    fin: int


@dataclass
class Cadre:
    jours: set
    debut: int
    fin: int
    duree_creneau: int
    duree_min: int
    duree_max: int
    pauses: list = field(default_factory=list)            # [(debut, fin)]
    indispo_prof: dict = field(default_factory=dict)      # prof -> [(jour, debut, fin)]
    indispo_salle: dict = field(default_factory=dict)     # salle -> [(jour, debut, fin)]
    capacites: dict = field(default_factory=dict)         # salle -> places
    effectifs: dict = field(default_factory=dict)         # (classe, groupe | None) -> eleves
    affectations: set = field(default_factory=set)        # (prof, matiere, classe, groupe | None)
    noms: dict = field(default_factory=dict)              # ("prof"|"salle"|"classe"|"matiere"|"groupe", id) -> nom

    def nom(self, genre, identifiant):
        return self.noms.get((genre, identifiant), f"{genre} {identifiant}")

    def creneaux_valides(self):
        """Index de creneaux (depuis le debut de journee) utilisables, hors pauses."""
        valides = []
        nombre = (self.fin - self.debut) // self.duree_creneau
        for index in range(nombre):
            a = self.debut + index * self.duree_creneau
            b = a + self.duree_creneau
            if not any(a < pb and pa < b for pa, pb in self.pauses):
                valides.append(index)
        return valides


def chevauche(a, b):
    return a.jour == b.jour and a.debut < b.fin and b.debut < a.fin


def _paires(seances):
    """Paires de seances qui se chevauchent (balayage trie, sans comparer tout avec tout)."""
    tri = sorted(seances, key=lambda s: (s.jour, s.debut, s.fin))
    for i, a in enumerate(tri):
        for b in tri[i + 1:]:
            if b.jour != a.jour or b.debut >= a.fin:
                break
            yield a, b


def _etiquette(cadre, s):
    texte = f"{cadre.nom('matiere', s.matiere)} - {cadre.nom('classe', s.classe)}"
    return texte + (f" ({cadre.nom('groupe', s.groupe)})" if s.groupe else "")


def _quand(s):
    return f"{NOMS_JOURS.get(s.jour, s.jour)} {hhmm(s.debut)}-{hhmm(s.fin)}"


def _conflit(type_, message, *seances):
    return {"type": type_, "message": message, "seances": [s.cle for s in seances]}


def detecter(seances, cadre, publication=False):
    conflits = []

    # --- ressources occupees deux fois au meme moment
    par_professeur, par_salle, par_classe = {}, {}, {}
    for s in seances:
        par_professeur.setdefault(s.professeur, []).append(s)
        if s.salle:
            par_salle.setdefault(s.salle, []).append(s)
        par_classe.setdefault(s.classe, []).append(s)

    for professeur, groupe in par_professeur.items():
        for a, b in _paires(groupe):
            conflits.append(_conflit(
                "PROFESSEUR_SIMULTANE",
                f"{cadre.nom('prof', professeur)} a deux cours en meme temps ({_quand(a)}) : "
                f"{_etiquette(cadre, a)} et {_etiquette(cadre, b)}.", a, b))
    for salle, groupe in par_salle.items():
        for a, b in _paires(groupe):
            conflits.append(_conflit(
                "SALLE_SIMULTANEE",
                f"La salle {cadre.nom('salle', salle)} est utilisee deux fois en meme temps ({_quand(a)}) : "
                f"{_etiquette(cadre, a)} et {_etiquette(cadre, b)}.", a, b))
    for classe, groupe in par_classe.items():
        for a, b in _paires(groupe):
            if a.groupe is None or b.groupe is None:
                conflits.append(_conflit(
                    "CLASSE_SIMULTANEE",
                    f"La classe {cadre.nom('classe', classe)} a deux cours en meme temps ({_quand(a)}) : "
                    f"{_etiquette(cadre, a)} et {_etiquette(cadre, b)}.", a, b))
            elif a.groupe == b.groupe:
                conflits.append(_conflit(
                    "GROUPE_SIMULTANE",
                    f"Le groupe {cadre.nom('groupe', a.groupe)} de {cadre.nom('classe', classe)} a deux cours en meme temps "
                    f"({_quand(a)}) : {_etiquette(cadre, a)} et {_etiquette(cadre, b)}.", a, b))

    # --- contraintes propres a chaque seance
    grille = cadre.duree_creneau
    for s in seances:
        for jour, a, b in cadre.indispo_prof.get(s.professeur, []):
            if jour == s.jour and s.debut < b and a < s.fin:
                conflits.append(_conflit(
                    "PROFESSEUR_INDISPONIBLE",
                    f"{cadre.nom('prof', s.professeur)} est indisponible le {NOMS_JOURS.get(jour)} de {hhmm(a)} a {hhmm(b)} "
                    f"({_etiquette(cadre, s)}, {_quand(s)}).", s))
                break
        if s.salle:
            for jour, a, b in cadre.indispo_salle.get(s.salle, []):
                if jour == s.jour and s.debut < b and a < s.fin:
                    conflits.append(_conflit(
                        "SALLE_INDISPONIBLE",
                        f"La salle {cadre.nom('salle', s.salle)} est indisponible le {NOMS_JOURS.get(jour)} de {hhmm(a)} a {hhmm(b)} "
                        f"({_etiquette(cadre, s)}, {_quand(s)}).", s))
                    break
        if s.jour not in cadre.jours:
            conflits.append(_conflit("HORS_HORAIRES", f"{NOMS_JOURS.get(s.jour, s.jour).capitalize()} n'est pas un jour ouvrable "
                                     f"({_etiquette(cadre, s)}).", s))
        elif s.debut < cadre.debut or s.fin > cadre.fin:
            conflits.append(_conflit("HORS_HORAIRES", f"{_etiquette(cadre, s)} ({_quand(s)}) depasse les horaires autorises "
                                     f"({hhmm(cadre.debut)}-{hhmm(cadre.fin)}).", s))
        elif any(s.debut < pb and pa < s.fin for pa, pb in cadre.pauses):
            conflits.append(_conflit("HORS_HORAIRES", f"{_etiquette(cadre, s)} ({_quand(s)}) chevauche une pause.", s))
        elif (s.debut - cadre.debut) % grille or (s.fin - s.debut) % grille:
            conflits.append(_conflit("HORS_HORAIRES", f"{_etiquette(cadre, s)} ({_quand(s)}) n'est pas aligne sur la grille "
                                     f"de creneaux de {grille} min.", s))
        duree = s.fin - s.debut
        if duree < cadre.duree_min or duree > cadre.duree_max:
            conflits.append(_conflit("DUREE", f"{_etiquette(cadre, s)} dure {duree} min : la duree doit etre comprise entre "
                                     f"{cadre.duree_min} et {cadre.duree_max} min.", s))
        if s.salle and s.salle in cadre.capacites:
            effectif = cadre.effectifs.get((s.classe, s.groupe), 0)
            if effectif > cadre.capacites[s.salle]:
                conflits.append(_conflit(
                    "CAPACITE_SALLE",
                    f"La salle {cadre.nom('salle', s.salle)} ({cadre.capacites[s.salle]} places) est trop petite pour "
                    f"{_etiquette(cadre, s)} ({effectif} eleves).", s))
        if cadre.affectations and (s.professeur, s.matiere, s.classe, None) not in cadre.affectations \
                and (s.professeur, s.matiere, s.classe, s.groupe) not in cadre.affectations:
            conflits.append(_conflit(
                "PROFESSEUR_NON_AFFECTE",
                f"{cadre.nom('prof', s.professeur)} n'est pas affecte a {_etiquette(cadre, s)} (voir Affectations des professeurs).", s))
        if publication and not s.salle:
            conflits.append(_conflit("SALLE_MANQUANTE", f"Aucune salle pour {_etiquette(cadre, s)} ({_quand(s)}).", s))
    return conflits


def conflits_de(cle, conflits):
    """Conflits qui impliquent la seance `cle` (pour valider un ajout ou un deplacement)."""
    return [c for c in conflits if cle in c["seances"]]
