"""Constantes metier partagees."""


class Role:
    ADMINISTRATEUR = "ADMINISTRATEUR"
    DIRECTEUR = "DIRECTEUR"
    RESPONSABLE_SCOLARITE = "RESPONSABLE_SCOLARITE"
    RESPONSABLE_PEDAGOGIQUE = "RESPONSABLE_PEDAGOGIQUE"
    COMPTABLE = "COMPTABLE"
    PROFESSEUR = "PROFESSEUR"

    CHOIX = [
        (ADMINISTRATEUR, "Administrateur"),
        (DIRECTEUR, "Directeur"),
        (RESPONSABLE_SCOLARITE, "Responsable de la scolarite"),
        (RESPONSABLE_PEDAGOGIQUE, "Responsable pedagogique"),
        (COMPTABLE, "Comptable"),
        (PROFESSEUR, "Professeur"),
    ]


# Modules visibles dans le menu, par role.
MODULES_PAR_ROLE = {
    Role.ADMINISTRATEUR: [
        "tableau_de_bord", "annees_scolaires", "niveaux", "classes", "tarifs", "groupes",
        "salles", "matieres", "etudiants", "inscriptions", "professeurs",
        "presences", "presences_professeurs", "notifications",
        "evaluations", "resultats", "emplois_du_temps", "planification", "disponibilites",
        "remuneration", "scolarite", "utilisateurs", "parametres",
    ],
    Role.DIRECTEUR: [
        "tableau_de_bord", "annees_scolaires", "niveaux", "classes", "tarifs", "groupes",
        "salles", "matieres", "etudiants", "inscriptions", "professeurs",
        "presences", "presences_professeurs", "notifications",
        "evaluations", "resultats", "emplois_du_temps", "planification", "disponibilites",
        "remuneration", "scolarite",
    ],
    Role.RESPONSABLE_SCOLARITE: [
        "tableau_de_bord", "etudiants", "inscriptions", "classes", "groupes",
        "presences", "notifications", "resultats", "emplois_du_temps",
    ],
    Role.RESPONSABLE_PEDAGOGIQUE: [
        "tableau_de_bord", "matieres", "classes", "groupes", "professeurs",
        "presences", "presences_professeurs", "evaluations", "resultats",
        "emplois_du_temps", "planification", "disponibilites",
    ],
    Role.COMPTABLE: [
        "tableau_de_bord", "tarifs", "scolarite", "professeurs", "remuneration",
    ],
    Role.PROFESSEUR: [
        "tableau_de_bord", "presences", "evaluations", "emplois_du_temps", "disponibilites", "ma_remuneration",
    ],
}


class Sexe:
    MASCULIN = "M"
    FEMININ = "F"
    CHOIX = [(MASCULIN, "Masculin"), (FEMININ, "Feminin")]


class StatutInscription:
    ACTIVE = "ACTIVE"
    TRANSFEREE = "TRANSFEREE"
    ABANDON = "ABANDON"
    DIPLOME = "DIPLOME"

    CHOIX = [
        (ACTIVE, "Active"),
        (TRANSFEREE, "Transferee"),
        (ABANDON, "Abandon"),
        (DIPLOME, "Diplome / fin de cycle"),
    ]


class TypeInscription:
    INSCRIPTION = "INSCRIPTION"
    REINSCRIPTION = "REINSCRIPTION"
    TRANSFERT = "TRANSFERT"
    CHOIX = [
        (INSCRIPTION, "Nouvelle inscription"),
        (REINSCRIPTION, "Reinscription"),
        (TRANSFERT, "Transfert depuis un autre etablissement"),
    ]


class StatutProfesseur:
    ACTIF = "ACTIF"
    INACTIF = "INACTIF"
    CHOIX = [(ACTIF, "Actif"), (INACTIF, "Inactif")]


class ModeRemuneration:
    HORAIRE = "HORAIRE"
    FIXE = "FIXE"
    CHOIX = [(HORAIRE, "Au nombre d'heures"), (FIXE, "Salaire fixe")]
