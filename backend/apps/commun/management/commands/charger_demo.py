"""Charge un jeu de donnees de DEMONSTRATION (ecole secondaire de Mauritanie) pour explorer
l'application ou lancer des tests de bout en bout. Jamais utilise en production : la commande
refuse de s'executer si la base contient deja des etudiants, sauf avec --ajouter qui complete la base
existante (annee active, niveaux et classes deja saisis) sans rien supprimer ni modifier."""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.emplois_du_temps import services as emplois
from apps.emplois_du_temps.models import ConfigurationHoraires, DisponibiliteProfesseur, EmploiDuTemps
from apps.etudiants.models import Etudiant, Inscription
from apps.evaluations import services as evaluations
from apps.evaluations.models import Evaluation, Note, StatutNote
from apps.presences import services as presences
from apps.presences.models import Seance
from apps.professeurs.models import AffectationProfesseur, Professeur
from apps.referentiels.models import (
    AffectationMatiereClasse, AnneeScolaire, Classe, Matiere, Niveau, Salle, TarifClasse,
)
from apps.remuneration import services as remuneration
from apps.scolarite.models import GrilleFrais, PaiementScolarite
from apps.utilisateurs.models import Utilisateur

# (nom, code, coefficient, seances/semaine, volume horaire hebdomadaire) - coefficients du bulletin papier
MATIERES = [
    ("I. Religieuse", "REL", 3, 2, 2), ("Arabe", "ARA", 5, 4, 4), ("H/G", "HG", 2, 2, 2), ("I. Civique", "CIV", 1, 1, 1),
    ("Francais", "FRA", 3, 3, 3), ("Anglais", "ANG", 1, 2, 2), ("Maths", "MAT", 5, 4, 4),
    ("Sc. Naturelles", "SN", 2, 2, 2), ("EPS", "EPS", 1, 2, 2),
]
NOMS_AR = {   # noms arabes des matieres (affiches quand l'interface est en arabe)
    "I. Religieuse": "التربية الإسلامية", "Arabe": "اللغة العربية", "H/G": "التاريخ والجغرافيا", "I. Civique": "التربية المدنية",
    "Francais": "اللغة الفرنسية", "Anglais": "اللغة الإنجليزية", "Maths": "الرياضيات", "Sc. Naturelles": "العلوم الطبيعية",
    "EPS": "التربية البدنية",
}
PROFESSEURS = [("Sy", "Oumar"), ("Ba", "Cheikh"), ("Fall", "Awa"), ("Sow", "Mamadou"), ("Diop", "Fatimata"),
               ("Kane", "Ibrahima"), ("Ndiaye", "Mariem"), ("Diallo", "Salif"), ("Camara", "Aminata")]
PRENOMS = ["Aziza", "Mohamed Lemine", "Fatimetou", "Cheikh", "Mariem", "Ahmed", "Khadijetou", "Sidi", "Aicha", "Brahim",
           "Zeinebou", "Abdallahi", "Oumou", "Yahya", "Meimouna", "Ely", "Salka", "Moctar", "Vatma", "Isselmou"]
NOMS = ["Abdallahi", "Ahmed", "Mohamed", "Sidi", "Brahim", "Ould Ely", "Vall", "Lemrabott", "Cheikh", "Mahmoud", "Salem", "Taleb"]
EVALUATIONS_T = [("Moy. interrogations", "INTERROGATION", 3), ("1ere composition", "EXAMEN", 1), ("2e composition", "EXAMEN", 2)]


def debut_annee(aujourdhui):
    return aujourdhui.year if aujourdhui.month >= 9 else aujourdhui.year - 1


class Command(BaseCommand):
    help = "Charge des donnees de demonstration (necessite --mot-de-passe pour les comptes crees)."

    def add_arguments(self, parser):
        parser.add_argument("--mot-de-passe", required=True, help="Mot de passe des comptes de demonstration (politique de securite appliquee).")
        parser.add_argument("--eleves-par-classe", type=int, default=10)
        parser.add_argument("--ajouter", action="store_true",
                            help="Ajoute la demonstration a une base deja utilisee (reutilise l'annee active, les niveaux et classes existants).")
        parser.add_argument("--graine", type=int, default=2026)

    def handle(self, *args, **options):
        self.ajouter = options["ajouter"]
        if self.ajouter:
            if PaiementScolarite.objects.filter(reference__startswith="SCOL-DEMO").exists():
                raise CommandError("La demonstration est deja chargee dans cette base.")
        elif Etudiant.objects.exists() or Professeur.objects.exists():
            raise CommandError("La base contient deja des donnees : utilisez --ajouter pour completer la base existante, "
                               "ou videz-la pour installer la demonstration complete.")
        from apps.utilisateurs.serializers import controler_mot_de_passe
        try:
            controler_mot_de_passe(options["mot_de_passe"])
        except ErreurMetier as e:
            raise CommandError(e.message)
        self.hasard = random.Random(options["graine"])
        self.mot_de_passe = options["mot_de_passe"]
        self.par_classe = options["eleves_par_classe"]
        self.aujourdhui = date.today()
        with transaction.atomic():
            self.referentiels()
            self.comptes()
            self.eleves()
            self.scolarite()
            self.evaluations()
            self.emploi_et_presences()
            self.remunerations()
        self.stdout.write(self.style.SUCCESS(
            f"Donnees de demonstration chargees (annee {self.annee.libelle}, classes : {', '.join(c.nom for c in self.classes)}). "
            "Comptes : admin, directeur, scolarite, pedagogie, comptable, prof1 (mot de passe = celui fourni ; "
            "les comptes qui existaient deja sont conserves tels quels)."))

    # ------------------------------------------------------------------ etapes

    def referentiels(self):
        if self.ajouter:
            self.annee = AnneeScolaire.objects.filter(active=True, archivee=False).first()
            if not self.annee:
                raise CommandError("Aucune annee scolaire active : activez-en une avant de charger la demonstration.")
            ConfigurationHoraires.objects.get_or_create(annee_scolaire=self.annee, defaults={"pauses": [{"debut": "10:00", "fin": "11:00"}]})
            # Les niveaux et classes saisis sont reutilises ; ceux qui manquent sont crees.
            definitions = [("Fondamental", "FOND", "6AF"), ("Lycee", "LYC", "7D"), ("College", "COLL", "1AS")]
            self.niveaux = [Niveau.objects.get_or_create(code=c, defaults={"nom": n, "ordre": i})[0] for i, (n, c, _) in enumerate(definitions, 1)]
            noms_classes = [nom for _, _, nom in definitions]
        else:
            self.creer_annee_demo()
            self.niveaux = [Niveau.objects.create(nom=n, code=c, ordre=i) for i, (n, c) in enumerate([("6eme", "6E"), ("7eme", "7E"), ("1ere AS", "1AS")], 1)]
            noms_classes = ["6AF", "7D", "1As"]
        self.salles = [Salle.objects.get_or_create(nom=f"S{i}", defaults={"capacite": 40, "type_salle": "Salle de classe"})[0] for i in range(1, 5)]
        self.classes = []
        for niveau, nom in zip(self.niveaux, noms_classes):
            classe, _ = Classe.objects.get_or_create(
                nom=nom, annee_scolaire=self.annee, defaults={"niveau": niveau, "capacite": 40, "salle_principale": self.salles[len(self.classes)]})
            self.classes.append(classe)
            TarifClasse.objects.get_or_create(classe=classe, defaults={"montant": [900, 1500, 2500][len(self.classes) - 1]})
        for niveau in self.niveaux:
            GrilleFrais.objects.get_or_create(
                annee_scolaire=self.annee, niveau=niveau, defaults={"montant_mensuel": 1500, "frais_inscription": 500, "nombre_mois": 9})
        self.matieres_et_professeurs()

    def creer_annee_demo(self):
        d = debut_annee(self.aujourdhui)
        self.annee = AnneeScolaire.objects.create(
            libelle=f"{d}-{d + 1}", date_debut=date(d, 9, 29), date_fin=date(d + 1, 6, 30), active=True,
            debut_trimestre2=date(d + 1, 1, 5), debut_trimestre3=date(d + 1, 4, 6),
            debut_vacances=date(d, 12, 20), fin_vacances=date(d + 1, 1, 4),
            debut_examen1=date(d, 12, 8), fin_examen1=date(d, 12, 18), debut_examen2=date(d + 1, 3, 16), fin_examen2=date(d + 1, 3, 27),
            debut_examen3=date(d + 1, 6, 8), fin_examen3=date(d + 1, 6, 20),
        )
        ConfigurationHoraires.objects.create(annee_scolaire=self.annee, pauses=[{"debut": "10:00", "fin": "11:00"}])

    def matieres_et_professeurs(self):
        self.matieres, self.professeurs = [], []
        for index, (nom, code, coefficient, seances, volume) in enumerate(MATIERES):
            matiere, _ = Matiere.objects.get_or_create(code=code, defaults={"nom": nom, "nom_ar": NOMS_AR.get(nom, "")})
            prof, _ = Professeur.objects.get_or_create(
                matricule=f"P{index + 1:03d}",
                defaults={"nom": PROFESSEURS[index][0], "prenom": PROFESSEURS[index][1], "tarif_horaire": 900,
                          "telephone": f"2{self.hasard.randint(2000000, 4999999)}", "specialite": nom})
            self.matieres.append(matiere)
            self.professeurs.append(prof)
            for classe in self.classes:
                AffectationMatiereClasse.objects.get_or_create(
                    matiere=matiere, classe=classe,
                    defaults={"coefficient": coefficient, "nombre_seances_semaine": seances, "volume_horaire_hebdo": volume})
                AffectationProfesseur.objects.get_or_create(professeur=prof, matiere=matiere, classe=classe, annee_scolaire=self.annee)
        DisponibiliteProfesseur.objects.get_or_create(
            professeur=self.professeurs[0], jour=4, defaults={"heure_debut": "11:00", "heure_fin": "14:00", "commentaire": "Indisponible le vendredi apres 11h"})

    def comptes(self):
        for identifiant, role, extra in [
            ("admin", Role.ADMINISTRATEUR, {"is_staff": True, "is_superuser": True}), ("directeur", Role.DIRECTEUR, {}),
            ("scolarite", Role.RESPONSABLE_SCOLARITE, {}), ("pedagogie", Role.RESPONSABLE_PEDAGOGIQUE, {}),
            ("comptable", Role.COMPTABLE, {}), ("prof1", Role.PROFESSEUR, {"professeur": self.professeurs[0]}),
        ]:
            if Utilisateur.objects.filter(identifiant=identifiant).exists():
                continue                                       # compte existant : conserve (mot de passe inchange)
            if "professeur" in extra and Utilisateur.objects.filter(professeur=extra["professeur"]).exists():
                continue                                       # ce professeur a deja son compte
            Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe=self.mot_de_passe, nom=identifiant.capitalize(), role=role, **extra)
        self.admin = (Utilisateur.objects.filter(identifiant="admin").first()
                      or Utilisateur.objects.filter(role=Role.ADMINISTRATEUR).first())

    def eleves(self):
        self.inscriptions = []
        compteur = 0
        for classe in self.classes:
            for _ in range(self.par_classe):
                compteur += 1
                while Etudiant.objects.filter(matricule=f"E{self.annee.date_debut.year % 100}{compteur:03d}").exists():
                    compteur += 1                              # matricule deja pris dans une base existante
                etudiant = Etudiant.objects.create(
                    matricule=f"E{self.annee.date_debut.year % 100}{compteur:03d}", nom=self.hasard.choice(NOMS), prenom=self.hasard.choice(PRENOMS),
                    sexe=self.hasard.choice("MF"), nom_pere=f"{self.hasard.choice(NOMS)} {self.hasard.choice(PRENOMS)}",
                    telephone_pere=f"{self.hasard.choice('234')}{self.hasard.randint(1000000, 9999999)}",
                    telephone_principal=f"{self.hasard.choice('234')}{self.hasard.randint(1000000, 9999999)}",
                    date_naissance=date(self.annee.date_debut.year - self.hasard.randint(11, 16), self.hasard.randint(1, 12), self.hasard.randint(1, 28)),
                    numero_national=f"Rim{self.hasard.randint(1000000, 9999999)}")
                self.inscriptions.append(Inscription.objects.create(
                    etudiant=etudiant, annee_scolaire=self.annee, classe=classe, date_inscription=self.annee.date_debut))

    def scolarite(self):
        for inscription in self.inscriptions:
            numero = inscription.etudiant.matricule
            PaiementScolarite.objects.create(
                reference=f"SCOL-DEMO-{numero}-I", inscription=inscription, type_frais="INSCRIPTION", montant=500,
                date_paiement=self.annee.date_debut, enregistre_par=self.admin)
            for mois in range(self.hasard.randint(1, 4)):
                premier = date(self.annee.date_debut.year + (1 if mois + 10 > 12 else 0), (mois + 9) % 12 + 1, 1)
                PaiementScolarite.objects.create(
                    reference=f"SCOL-DEMO-{numero}-{mois}", inscription=inscription, type_frais="MENSUALITE", mois_concerne=premier,
                    montant=1500, date_paiement=min(premier + timedelta(days=self.hasard.randint(0, 6)), self.aujourdhui), enregistre_par=self.admin)

    def evaluations(self):
        """T1 complet et valide ; T2 en cours (notes encore a saisir)."""
        for classe in self.classes:
            eleves = [i.etudiant for i in self.inscriptions if i.classe_id == classe.id]
            for matiere in self.matieres:
                for trimestre, nb in ((1, 3), (2, 2)):
                    for numero, (libelle, type_, poids) in enumerate(EVALUATIONS_T[:nb]):
                        jour = date(self.annee.date_debut.year, 10, 1) + timedelta(days=30 * (trimestre - 1) * 3 + numero * 25)
                        evaluation = Evaluation.objects.create(
                            annee_scolaire=self.annee, classe=classe, matiere=matiere, trimestre=trimestre, libelle=libelle,
                            type=type_, poids=poids, bareme=20, date=min(jour, self.annee.date_fin))
                        for etudiant in eleves:
                            if trimestre == 2 and numero == 1 and self.hasard.random() < 0.4:
                                continue                       # note du 2e trimestre pas encore saisie
                            if self.hasard.random() < 0.03:
                                Note.objects.create(evaluation=evaluation, etudiant=etudiant, statut=StatutNote.ABSENT_JUSTIFIE)
                            else:
                                Note.objects.create(evaluation=evaluation, etudiant=etudiant, valeur=Decimal(str(round(self.hasard.uniform(4, 19.5) * 4) / 4)))
            # Dans une base existante, la classe peut compter d'autres eleves sans notes : validation acceptee quand meme.
            evaluations.valider_resultats(classe, 1, self.admin, accepter_incomplet=self.ajouter)

    def emploi_et_presences(self):
        if self.ajouter and EmploiDuTemps.objects.filter(annee_scolaire=self.annee, statut="PUBLIE").exists():
            self.stdout.write(self.style.WARNING("Un emploi du temps est deja publie pour cette annee : celui de demonstration n'est pas genere."))
            return
        emploi = emplois.generer_emploi(self.annee, self.admin, "Emploi du temps de demonstration", graine=7, temps_max=15)
        if not emploi.rapport.get("publiable"):
            self.stdout.write(self.style.WARNING("L'emploi du temps genere n'est pas publiable : seances de presence non creees."))
            return
        emplois.publier_emploi(emploi, self.admin, "Version de demonstration")
        fin = min(self.aujourdhui, self.annee.date_fin)
        debut = max(fin - timedelta(days=14), self.annee.date_debut)
        if debut >= fin:
            return
        emplois.generer_seances_presence(emploi, debut, fin, self.admin)
        for seance in Seance.objects.filter(date__lte=fin).select_related("professeur"):
            tirage = self.hasard.random()
            seance.statut_professeur = "ABSENT" if tirage < 0.04 else "ANNULE" if tirage < 0.07 else "EFFECTUE"
            seance.save()
            if seance.statut_professeur == "ANNULE" or seance.date == fin:
                continue                                       # annulee ou du jour : liste d'appel non validee
            lignes = [{"etudiant": i.etudiant_id, "statut": self.hasard.choices(["PRESENT", "ABSENT", "RETARD"], [88, 9, 3])[0]}
                      for i in presences.eleves_classe(seance.classe_id, seance.annee_scolaire_id)]
            presences.enregistrer_presences(seance, lignes)
            presences.valider_seance(seance, self.admin)

    def remunerations(self):
        precedent = (self.aujourdhui.replace(day=1) - timedelta(days=1)).replace(day=1)
        for mois in (precedent, self.aujourdhui.replace(day=1)):
            for professeur in self.professeurs:
                if remuneration.seances_du_professeur(professeur, mois, remuneration.dernier_du_mois(mois)).exists():
                    remuneration.generer_releve(professeur, mois, self.admin)
        from apps.remuneration.models import ReleveRemuneration
        for releve in ReleveRemuneration.objects.filter(mois=precedent):
            valide = remuneration.valider_releve(releve, self.admin)
            net = remuneration.totaux(valide)["net"]
            if net > 0:
                remuneration.enregistrer_paiement(valide, (net / 2).quantize(Decimal("0.01")), "VIREMENT", self.aujourdhui, "Acompte", self.admin)
