"""Generation automatique d'emploi du temps par algorithme genetique (module pur).

Chromosome : une position (jour, creneau de depart, salle) par unite a placer
(une unite = une seance hebdomadaire d'une matiere pour une classe/un groupe,
avec son professeur et sa duree en creneaux).

Fitness (a MINIMISER) = 1000 x violations des contraintes obligatoires
(professeur/salle/classe/groupe simultanes, indisponibilites)
+ penalites des preferences (heures creuses, repartition, seances
consecutives, jour trop charge, changement de salle, creneaux preferes).
Les contraintes obligatoires dominent toujours les preferences. Le
resultat est ensuite reverifie par `conflits.detecter` : un emploi du
temps avec un conflit restant n'est jamais presente comme valide."""

import random
import time as horloge
from collections import Counter, defaultdict
from dataclasses import dataclass, field

POIDS_DUR = 1000
W_TROU = 3          # creneau libre entre deux cours d'une classe
W_MAX_JOUR = 5      # creneau au-dela du maximum quotidien d'un professeur
W_CONSECUTIF = 4    # creneau au-dela du maximum de creneaux consecutifs d'un professeur
W_MEME_JOUR = 4     # meme matiere deux fois le meme jour pour une classe
W_SALLE = 1         # cours hors de la salle habituelle de la classe
W_PREFERE = 2       # creneau hors des preferences du professeur (prime sur l'equilibre des jours)
W_EQUILIBRE = 1     # ecart de charge entre le jour le plus et le moins charge d'une classe


@dataclass
class Unite:
    cle: int
    classe: int
    groupe: object
    matiere: int
    professeur: int
    longueur: int                                   # en creneaux
    salles: list = field(default_factory=lambda: [None])
    salle_preferee: object = None


@dataclass
class Solution:
    genes: list
    violations: int
    penalites: int
    generations: int
    duree: float
    arret: str


class Probleme:
    def __init__(self, unites, cadre, preferences=None, max_jour=6, max_consecutifs=4):
        self.unites = unites
        self.cadre = cadre
        self.max_jour = max_jour
        self.max_consecutifs = max_consecutifs
        self.jours = sorted(cadre.jours)
        self.nb_creneaux = (cadre.fin - cadre.debut) // cadre.duree_creneau
        self.valides = set(cadre.creneaux_valides())
        self.positions = [self._positions(u) for u in unites]
        self.bloque_prof = self._bloques(cadre.indispo_prof)
        self.bloque_salle = self._bloques(cadre.indispo_salle)
        self.preferes = defaultdict(set)
        for prof, liste in (preferences or {}).items():
            for jour, a, b in liste:
                self.preferes[(prof, jour)] |= self._creneaux_couverts(a, b)
        self.profs_avec_preferences = {prof for prof in (preferences or {}) if preferences[prof]}

    def _creneaux_couverts(self, a, b):
        d = self.cadre.duree_creneau
        return {k for k in range(self.nb_creneaux)
                if self.cadre.debut + k * d < b and a < self.cadre.debut + (k + 1) * d}

    def _bloques(self, indispo):
        resultat = {}
        for identifiant, liste in indispo.items():
            for jour, a, b in liste:
                resultat.setdefault((identifiant, jour), set()).update(self._creneaux_couverts(a, b))
        return resultat

    def _positions(self, unite):
        return [
            (jour, depart) for jour in self.jours
            for depart in range(self.nb_creneaux - unite.longueur + 1)
            if all(k in self.valides for k in range(depart, depart + unite.longueur))
        ]

    def gene_aleatoire(self, i, rng):
        unite = self.unites[i]
        jour, depart = rng.choice(self.positions[i])
        if unite.salle_preferee is not None and rng.random() < 0.6:
            salle = unite.salle_preferee
        else:
            salle = rng.choice(unite.salles)
        return (jour, depart, salle)

    # ------------------------------------------------------------ evaluation

    def occupation(self):
        return Occupation(self)

    def evaluer(self, genes):
        occupation = self.occupation()
        violations = 0
        for unite, gene in zip(self.unites, genes):
            violations += occupation.conflits(unite, gene)
            occupation.ajouter(unite, gene)
        return violations, self.penalites(genes)

    def penalites(self, genes):
        total = 0
        classe_jour, prof_jour, classe_matiere = defaultdict(set), defaultdict(set), defaultdict(list)
        for unite, (jour, depart, salle) in zip(self.unites, genes):
            creneaux = range(depart, depart + unite.longueur)
            classe_jour[(unite.classe, jour)].update(creneaux)
            prof_jour[(unite.professeur, jour)].update(creneaux)
            classe_matiere[(unite.classe, unite.matiere, unite.groupe)].append(jour)
            if unite.salle_preferee is not None and salle != unite.salle_preferee:
                total += W_SALLE
            if unite.professeur in self.profs_avec_preferences:
                preferes = self.preferes.get((unite.professeur, jour), ())
                total += W_PREFERE * sum(1 for k in creneaux if k not in preferes)
        charges = defaultdict(dict)
        for (classe, jour), creneaux in classe_jour.items():
            haut, bas = max(creneaux), min(creneaux)
            total += W_TROU * sum(1 for k in range(bas, haut + 1) if k in self.valides and k not in creneaux)
            charges[classe][jour] = len(creneaux)
        for classe, par_jour in charges.items():
            valeurs = [par_jour.get(j, 0) for j in self.jours]
            total += W_EQUILIBRE * (max(valeurs) - min(valeurs))
        for creneaux in prof_jour.values():
            if len(creneaux) > self.max_jour:
                total += W_MAX_JOUR * (len(creneaux) - self.max_jour)
            serie = 0
            precedent = None
            for k in sorted(creneaux):
                serie = serie + 1 if precedent is not None and k == precedent + 1 else 1
                if serie > self.max_consecutifs:
                    total += W_CONSECUTIF
                precedent = k
        for jours in classe_matiere.values():
            total += W_MEME_JOUR * sum(n - 1 for n in Counter(jours).values() if n > 1)
        return total


class Occupation:
    """Occupation incrementale des ressources, pour compter les conflits d'un placement."""

    def __init__(self, probleme):
        self.p = probleme
        self.prof = defaultdict(int)
        self.salle = defaultdict(int)
        self.classe_entiere = defaultdict(int)
        self.classe_groupe = defaultdict(int)
        self.classe_total = defaultdict(int)

    def conflits(self, unite, gene):
        jour, depart, salle = gene
        bloque_prof = self.p.bloque_prof.get((unite.professeur, jour), ())
        bloque_salle = self.p.bloque_salle.get((salle, jour), ()) if salle is not None else ()
        total = 0
        for k in range(depart, depart + unite.longueur):
            total += self.prof.get((unite.professeur, jour, k), 0)
            if salle is not None:
                total += self.salle.get((salle, jour, k), 0)
            if unite.groupe is None:
                total += self.classe_total.get((unite.classe, jour, k), 0)
            else:
                total += (self.classe_entiere.get((unite.classe, jour, k), 0)
                          + self.classe_groupe.get((unite.classe, unite.groupe, jour, k), 0))
            total += (k in bloque_prof) + (k in bloque_salle)
        return total

    def ajouter(self, unite, gene, signe=1):
        jour, depart, salle = gene
        for k in range(depart, depart + unite.longueur):
            self.prof[(unite.professeur, jour, k)] += signe
            if salle is not None:
                self.salle[(salle, jour, k)] += signe
            self.classe_total[(unite.classe, jour, k)] += signe
            if unite.groupe is None:
                self.classe_entiere[(unite.classe, jour, k)] += signe
            else:
                self.classe_groupe[(unite.classe, unite.groupe, jour, k)] += signe

    def retirer(self, unite, gene):
        self.ajouter(unite, gene, -1)


def diagnostiquer(probleme):
    """Ressources manifestement insuffisantes ou contraintes incompatibles, AVANT la
    recherche : charge d'un professeur ou d'une classe superieure aux creneaux
    disponibles, seance qui ne tient dans aucun creneau, manque de salles."""
    cadre = probleme.cadre
    par_semaine = len(probleme.jours) * len(probleme.valides)
    messages = []
    for unite, positions in zip(probleme.unites, probleme.positions):
        if not positions:
            messages.append(
                f"{cadre.nom('matiere', unite.matiere)} - {cadre.nom('classe', unite.classe)} : une seance de "
                f"{unite.longueur} creneau(x) consecutif(s) ne tient dans aucune journee (pauses, horaires).")

    charge_professeur = defaultdict(int)
    entiere, groupes = defaultdict(int), defaultdict(lambda: defaultdict(int))
    for unite in probleme.unites:
        charge_professeur[unite.professeur] += unite.longueur
        if unite.groupe is None:
            entiere[unite.classe] += unite.longueur
        else:
            groupes[unite.classe][unite.groupe] += unite.longueur
    for professeur, charge in charge_professeur.items():
        bloques = sum(len([k for k in probleme.bloque_prof.get((professeur, j), ()) if k in probleme.valides])
                      for j in probleme.jours)
        if charge > par_semaine - bloques:
            messages.append(
                f"{cadre.nom('prof', professeur)} doit assurer {charge} creneaux par semaine mais n'en a que "
                f"{par_semaine - bloques} de disponibles (indisponibilites comprises).")
    for classe in set(entiere) | set(groupes):
        charge = entiere[classe] + max(groupes[classe].values(), default=0)
        if charge > par_semaine:
            messages.append(
                f"La classe {cadre.nom('classe', classe)} necessite {charge} creneaux par semaine pour {par_semaine} disponibles.")
    salles = {s for u in probleme.unites for s in u.salles if s is not None}
    besoin_salle = sum(u.longueur for u in probleme.unites if u.salles != [None])
    if salles and besoin_salle > len(salles) * par_semaine:
        messages.append(
            f"{besoin_salle} creneaux de salle sont necessaires par semaine, mais {len(salles)} salle(s) n'offrent que "
            f"{len(salles) * par_semaine} creneaux.")
    return messages


# --------------------------------------------------------------- operateurs

def individu_glouton(probleme, rng, essais):
    """Construction aleatoire guidee : chaque unite prend, parmi `essais` positions
    tirees au hasard, celle qui provoque le moins de conflits."""
    unites = probleme.unites
    occupation = probleme.occupation()
    ordre = sorted(range(len(unites)), key=lambda i: (-unites[i].longueur, len(probleme.positions[i]) + rng.random() * 5))
    genes = [None] * len(unites)
    for i in ordre:
        meilleur, meilleur_conflit = None, None
        for _ in range(essais):
            gene = probleme.gene_aleatoire(i, rng)
            conflit = occupation.conflits(unites[i], gene)
            if meilleur is None or conflit < meilleur_conflit:
                meilleur, meilleur_conflit = gene, conflit
                if conflit == 0:
                    break
        genes[i] = meilleur
        occupation.ajouter(unites[i], meilleur)
    return genes


def reparer(probleme, genes, rng, passes=3, essais=25):
    """Recherche locale : deplace chaque unite en conflit vers la meilleure position trouvee."""
    unites = probleme.unites
    occupation = probleme.occupation()
    for unite, gene in zip(unites, genes):
        occupation.ajouter(unite, gene)
    for _ in range(passes):
        en_conflit = []
        for i, unite in enumerate(unites):
            occupation.retirer(unite, genes[i])
            if occupation.conflits(unite, genes[i]) > 0:
                en_conflit.append(i)
            occupation.ajouter(unite, genes[i])
        if not en_conflit:
            break
        rng.shuffle(en_conflit)
        for i in en_conflit:
            unite = unites[i]
            occupation.retirer(unite, genes[i])
            meilleur, meilleur_conflit = genes[i], occupation.conflits(unite, genes[i])
            for _ in range(essais):
                if meilleur_conflit == 0:
                    break
                candidat = probleme.gene_aleatoire(i, rng)
                conflit = occupation.conflits(unite, candidat)
                if conflit < meilleur_conflit:
                    meilleur, meilleur_conflit = candidat, conflit
            genes[i] = meilleur
            occupation.ajouter(unite, meilleur)
    return genes


def croiser(parent_a, parent_b, rng):
    return [a if rng.random() < 0.5 else b for a, b in zip(parent_a, parent_b)]


def muter(probleme, genes, rng, taux):
    for i in range(len(genes)):
        if rng.random() < taux:
            genes[i] = probleme.gene_aleatoire(i, rng)
    return genes


def _note(evaluation):
    violations, penalites = evaluation
    return violations * POIDS_DUR + penalites


def resoudre(probleme, graine=None, population=30, generations=200, temps_max=20.0,
             taux_mutation=0.04, elite=2, patience=40):
    """Lance l'algorithme ; retourne la meilleure `Solution` trouvee."""
    rng = random.Random(graine)
    debut = horloge.monotonic()
    n = len(probleme.unites)
    if n == 0:
        return Solution([], 0, 0, 0, 0.0, "aucune seance a placer")

    individus = []
    for k in range(population):
        genes = individu_glouton(probleme, rng, essais=40 if k < population // 3 else 6)
        genes = reparer(probleme, genes, rng, passes=2)
        individus.append((_note(probleme.evaluer(genes)), genes))
    individus.sort(key=lambda t: t[0])

    meilleure_note, sans_progres, generation, arret = individus[0][0], 0, 0, "generations maximales atteintes"
    for generation in range(1, generations + 1):
        if horloge.monotonic() - debut > temps_max:
            arret = "temps maximal atteint"
            break
        if individus[0][0] < POIDS_DUR and sans_progres >= patience:
            arret = "solution stable (aucun progres)"
            break
        suivants = [(note, list(genes)) for note, genes in individus[:elite]]
        while len(suivants) < population:
            a = min(rng.sample(individus, min(3, len(individus))), key=lambda t: t[0])[1]
            b = min(rng.sample(individus, min(3, len(individus))), key=lambda t: t[0])[1]
            enfant = muter(probleme, croiser(a, b, rng), rng, taux_mutation)
            if rng.random() < 0.5:
                enfant = reparer(probleme, enfant, rng, passes=1)
            suivants.append((_note(probleme.evaluer(enfant)), enfant))
        suivants.sort(key=lambda t: t[0])
        individus = suivants
        if individus[0][0] < meilleure_note:
            meilleure_note, sans_progres = individus[0][0], 0
        else:
            sans_progres += 1

    note, genes = individus[0]
    if note >= POIDS_DUR:  # derniere chance : reparation intensive de la meilleure solution
        genes = reparer(probleme, list(genes), rng, passes=15, essais=80)
    violations, penalites = probleme.evaluer(genes)
    return Solution(genes, violations, penalites, generation, round(horloge.monotonic() - debut, 2), arret)
