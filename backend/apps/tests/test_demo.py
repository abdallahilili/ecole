from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.etudiants.models import Etudiant
from apps.evaluations.models import ValidationResultats
from apps.emplois_du_temps.models import EmploiDuTemps
from apps.presences.models import Seance
from apps.utilisateurs.models import Utilisateur


class ChargementDemoTests(TestCase):
    def test_la_demonstration_se_charge_et_reste_coherente(self):
        call_command("charger_demo", mot_de_passe="Demo-Ecole-2026!", eleves_par_classe=4)
        self.assertEqual(Etudiant.objects.count(), 12)
        self.assertEqual(ValidationResultats.objects.count(), 3)                       # T1 valide pour les 3 classes
        self.assertEqual(EmploiDuTemps.objects.filter(statut="PUBLIE").count(), 1)
        self.assertEqual(Utilisateur.objects.count(), 6)
        admin = Utilisateur.objects.get(identifiant="admin")
        self.assertTrue(admin.check_password("Demo-Ecole-2026!"))                       # jamais de mot de passe par defaut
        # Aucune seance n'est comptee sans heures valides : les statuts annulee/absente donnent 0 heure.
        for seance in Seance.objects.filter(statut_professeur__in=("ABSENT", "ANNULE")):
            self.assertEqual(seance.heures_effectuees, 0)

    def test_refus_sur_une_base_non_vide_et_mot_de_passe_faible(self):
        with self.assertRaises(CommandError):
            call_command("charger_demo", mot_de_passe="123")
        call_command("charger_demo", mot_de_passe="Demo-Ecole-2026!", eleves_par_classe=2)
        with self.assertRaises(CommandError):
            call_command("charger_demo", mot_de_passe="Demo-Ecole-2026!")


class AjoutDemoBaseExistanteTests(TestCase):
    def setUp(self):
        from datetime import date
        from apps.commun.constantes import Role
        from apps.etudiants.models import Inscription
        from apps.professeurs.models import Professeur
        from apps.referentiels.models import AnneeScolaire, Classe, Niveau
        self.annee = AnneeScolaire.objects.create(libelle="2026-2027", date_debut=date(2026, 10, 5), date_fin=date(2027, 6, 30), active=True)
        niveau = Niveau.objects.create(nom="Fondamental", code="FOND", ordre=1)
        self.classe = Classe.objects.create(nom="6AF", niveau=niveau, annee_scolaire=self.annee)
        self.admin = Utilisateur.objects.create_user(identifiant="admin", mot_de_passe="Mon-Mot-De-Passe-1!", nom="Admin", role=Role.ADMINISTRATEUR)
        self.prof = Professeur.objects.create(matricule="P001", nom="Existant", prenom="Prof", tarif_horaire=500)
        reel = Etudiant.objects.create(matricule="E26001", nom="Reel", prenom="Eleve")
        Inscription.objects.create(etudiant=reel, annee_scolaire=self.annee, classe=self.classe, date_inscription=date(2026, 10, 5))

    def test_ajout_sans_rien_casser(self):
        call_command("charger_demo", mot_de_passe="Demo-Ecole-2026!", eleves_par_classe=3, ajouter=True)
        self.assertEqual(Etudiant.objects.count(), 1 + 9)
        self.assertEqual(Etudiant.objects.get(matricule="E26001").nom, "Reel")
        self.assertEqual(self.classe.__class__.objects.filter(annee_scolaire=self.annee, nom="6AF").count(), 1)   # classe reutilisee
        self.assertTrue(Utilisateur.objects.get(identifiant="admin").check_password("Mon-Mot-De-Passe-1!"))      # mot de passe conserve
        self.prof.refresh_from_db()
        self.assertEqual(self.prof.nom, "Existant")
        self.assertEqual(ValidationResultats.objects.count(), 3)
        with self.assertRaises(CommandError):                                                                     # pas de double chargement
            call_command("charger_demo", mot_de_passe="Demo-Ecole-2026!", ajouter=True)
