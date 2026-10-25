from datetime import date, time, timedelta
from decimal import Decimal as D

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.commun.constantes import Role
from apps.emplois_du_temps.models import EmploiDuTemps, SeanceProgrammee
from apps.etudiants.models import Etudiant, Inscription
from apps.evaluations.models import Evaluation, Note, ValidationResultats
from apps.presences.models import NotificationWhatsApp, PresenceEtudiant, Seance
from apps.professeurs.models import AffectationProfesseur, Professeur
from apps.referentiels.models import AffectationMatiereClasse, AnneeScolaire, Classe, Matiere, Niveau, Salle
from apps.remuneration import services as remuneration
from apps.scolarite.models import PaiementScolarite
from apps.utilisateurs.models import Utilisateur

URL = "/api/tableau-de-bord/"

SECTIONS_ATTENDUES = {
    Role.ADMINISTRATEUR: {"effectifs", "structure", "presences_etudiants", "presences_professeurs", "notifications",
                          "remuneration", "scolarite", "emploi_du_temps", "evaluations"},
    Role.DIRECTEUR: {"effectifs", "structure", "presences_etudiants", "presences_professeurs", "notifications",
                     "remuneration", "scolarite", "emploi_du_temps", "evaluations"},
    Role.RESPONSABLE_SCOLARITE: {"effectifs", "structure", "presences_etudiants", "notifications"},
    Role.RESPONSABLE_PEDAGOGIQUE: {"structure", "evaluations", "presences_etudiants", "presences_professeurs", "emploi_du_temps"},
    Role.COMPTABLE: {"scolarite", "remuneration"},
    Role.PROFESSEUR: {"mon_espace"},
}


def utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin", **extra):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="motdepasse123", nom="Test", role=role, **extra)


def client_de(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class BaseTableau(TestCase):
    def setUp(self):
        self.aujourdhui = timezone.localdate()
        self.annee = AnneeScolaire.objects.create(
            libelle="Annee en cours", date_debut=self.aujourdhui - timedelta(days=120), date_fin=self.aujourdhui + timedelta(days=200),
            active=True, debut_trimestre2=self.aujourdhui - timedelta(days=30), debut_trimestre3=self.aujourdhui + timedelta(days=60))
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.af = Classe.objects.create(nom="6AF", niveau=self.niveau, annee_scolaire=self.annee, capacite=40)
        self.d = Classe.objects.create(nom="7D", niveau=self.niveau, annee_scolaire=self.annee, capacite=40)
        self.maths = Matiere.objects.create(nom="Maths", code="MATH")
        self.sy = Professeur.objects.create(matricule="P1", nom="Sy", prenom="Oumar", tarif_horaire=100)
        self.ba = Professeur.objects.create(matricule="P2", nom="Ba", prenom="Cheikh", tarif_horaire=100)
        self.awa = self.eleve("E1", "Diallo", "Awa", self.af)
        self.moussa = self.eleve("E2", "Ba", "Moussa", self.af)
        self.fall = self.eleve("E3", "Fall", "Mariam", self.d)
        self.admin = utilisateur()
        self.client = client_de(self.admin)

    def eleve(self, matricule, nom, prenom, classe):
        etudiant = Etudiant.objects.create(matricule=matricule, nom=nom, prenom=prenom)
        Inscription.objects.create(etudiant=etudiant, annee_scolaire=self.annee, classe=classe, date_inscription=self.annee.date_debut)
        return etudiant

    def seance(self, jours_avant=1, heure=8, prof=None, classe=None, **extra):
        defauts = dict(annee_scolaire=self.annee, classe=classe or self.af, matiere=self.maths, professeur=prof or self.sy,
                       date=self.aujourdhui - timedelta(days=jours_avant), heure_debut=time(heure), heure_fin=time(heure + 1))
        defauts.update(extra)
        return Seance.objects.create(**defauts)

    def donnees(self, client=None):
        reponse = (client or self.client).get(URL)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        return reponse.json()


class RolesTests(BaseTableau):
    def test_chaque_role_ne_recoit_que_ses_sections(self):
        for role, attendues in SECTIONS_ATTENDUES.items():
            donnees = self.donnees(client_de(utilisateur(role, f"u_{role}")))
            self.assertEqual(set(donnees["sections"]), attendues, role)
            self.assertEqual(donnees["role"], role)
            self.assertEqual(donnees["annee_scolaire"]["libelle"], "Annee en cours")

    def test_acces_anonyme_refuse(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)

    def test_aucune_donnee_financiere_pour_les_roles_sans_droit(self):
        for role in (Role.RESPONSABLE_SCOLARITE, Role.RESPONSABLE_PEDAGOGIQUE, Role.PROFESSEUR):
            sections = self.donnees(client_de(utilisateur(role, f"x_{role}")))["sections"]
            self.assertNotIn("remuneration", sections)
            self.assertNotIn("scolarite", sections)

    def test_base_vide_pas_d_erreur_ni_de_chiffres_inventes(self):
        for modele in (Inscription, Evaluation, Seance, Classe, AnneeScolaire):   # ordre : les references protegees d'abord
            modele.objects.all().delete()
        donnees = self.donnees()
        self.assertIsNone(donnees["annee_scolaire"])
        sections = donnees["sections"]
        self.assertEqual(sections["effectifs"]["etudiants_actifs"], 0)
        self.assertEqual(sections["presences_etudiants"]["total"], 0)
        self.assertIsNone(sections["presences_etudiants"]["taux_presence"])
        self.assertEqual(sections["remuneration"]["montants_dus"], "0.00")
        self.assertEqual(sections["evaluations"]["prochaines"], [])
        self.assertIsNone(sections["emploi_du_temps"]["publie"])


class ChiffresTests(BaseTableau):
    def test_effectifs_et_structure(self):
        sections = self.donnees()["sections"]
        self.assertEqual(sections["effectifs"]["etudiants_actifs"], 3)
        self.assertEqual({c["classe"]: c["effectif"] for c in sections["effectifs"]["par_classe"]}, {"6AF": 2, "7D": 1})
        self.assertEqual(sections["effectifs"]["par_niveau"], [{"niveau": "6eme", "effectif": 3}])
        self.assertEqual((sections["structure"]["classes"], sections["structure"]["professeurs_actifs"], sections["structure"]["matieres"]), (2, 2, 1))
        Inscription.objects.filter(etudiant=self.fall).update(statut="ABANDON")
        self.assertEqual(self.donnees()["sections"]["effectifs"]["etudiants_actifs"], 2)

    def test_presences_des_etudiants_seulement_les_seances_validees(self):
        validee = self.seance(heure=8, presences_validees=True)
        PresenceEtudiant.objects.create(seance=validee, etudiant=self.awa, statut="PRESENT")
        PresenceEtudiant.objects.create(seance=validee, etudiant=self.moussa, statut="ABSENT")
        brouillon = self.seance(heure=9)
        PresenceEtudiant.objects.create(seance=brouillon, etudiant=self.awa, statut="ABSENT")        # non validee : ignoree
        ancienne = self.seance(jours_avant=90, heure=10, presences_validees=True)
        PresenceEtudiant.objects.create(seance=ancienne, etudiant=self.awa, statut="ABSENT")         # hors fenetre de 30 jours
        p = self.donnees()["sections"]["presences_etudiants"]
        self.assertEqual((p["total"], p["presents"], p["absents"], p["taux_presence"]), (2, 1, 1, 50.0))
        self.assertEqual([a["etudiant"] for a in p["dernieres_absences"]], ["Ba Moussa"])

    def test_presences_des_professeurs_et_heures(self):
        self.seance(heure=8, statut_professeur="EFFECTUE", heure_fin=time(10))      # 2 h
        self.seance(heure=11, statut_professeur="EFFECTUE")                         # 1 h
        self.seance(heure=12, statut_professeur="ABSENT")
        self.seance(heure=13)                                                       # planifiee : a renseigner
        p = self.donnees()["sections"]["presences_professeurs"]
        self.assertEqual((p["seances_effectuees"], p["absences"], p["a_renseigner"]), (2, 1, 1))
        self.assertEqual((p["taux_realisation"], p["heures_effectuees"]), (66.7, "3.00"))

    def test_notifications(self):
        seance = self.seance(presences_validees=True)
        for etudiant, statut in ((self.awa, "EN_ATTENTE"), (self.moussa, "ECHEC"), (self.fall, "ENVOYE")):
            presence = PresenceEtudiant.objects.create(seance=seance, etudiant=etudiant, statut="ABSENT")
            NotificationWhatsApp.objects.create(presence=presence, telephone="22222288896", message="x", statut=statut)
        n = self.donnees()["sections"]["notifications"]
        self.assertEqual((n["en_attente"], n["echecs"], n["envoyees"]), (1, 1, 1))

    def test_remuneration_et_scolarite(self):
        self.seance(heure=8, statut_professeur="EFFECTUE", heure_fin=time(10))      # 2 h x 100
        releve = remuneration.generer_releve(self.sy, self.aujourdhui - timedelta(days=1), self.admin)
        r = remuneration.valider_releve(releve, self.admin)
        remuneration.enregistrer_paiement(r, "50", "ESPECES", self.aujourdhui, "", self.admin)
        sections = self.donnees()["sections"]
        self.assertEqual(sections["remuneration"]["montants_dus"], "150.00")        # 200 - 50
        self.assertEqual(sections["remuneration"]["derniers_paiements"][0]["montant"], "50.00")
        ins = Inscription.objects.get(etudiant=self.awa)
        PaiementScolarite.objects.create(reference="SCOL-1", inscription=ins, type_frais="MENSUALITE", mois_concerne=self.aujourdhui.replace(day=1),
                                         montant=1500, date_paiement=self.aujourdhui, enregistre_par=self.admin)
        s = self.donnees()["sections"]["scolarite"]
        self.assertEqual((s["encaisse_mois"], s["nombre_paiements_mois"]), ("1500.00", 1))
        self.assertEqual(s["derniers_paiements"][0]["etudiant"], "Diallo Awa")

    def test_emploi_du_temps(self):
        emploi = EmploiDuTemps.objects.create(annee_scolaire=self.annee, nom="Officiel", statut="PUBLIE", publie_le=timezone.now())
        SeanceProgrammee.objects.create(emploi=emploi, classe=self.af, matiere=self.maths, professeur=self.sy, jour=0,
                                        heure_debut=time(8), heure_fin=time(9))
        EmploiDuTemps.objects.create(annee_scolaire=self.annee, nom="Brouillon", rapport={"publiable": False, "conflits": ["a", "b"]})
        e = self.donnees()["sections"]["emploi_du_temps"]
        self.assertEqual((e["publie"]["nom"], e["publie"]["seances"], e["brouillons"]), ("Officiel", 1, 1))
        self.assertEqual((e["derniere_generation"]["publiable"], e["derniere_generation"]["conflits"]), (False, 2))

    def test_evaluations_notes_manquantes_resultats_a_valider_prochaines(self):
        AffectationMatiereClasse.objects.create(matiere=self.maths, classe=self.af, coefficient=2)
        passee = Evaluation.objects.create(annee_scolaire=self.annee, classe=self.af, matiere=self.maths, trimestre=2,
                                           libelle="Composition 1", date=self.aujourdhui - timedelta(days=3))
        Note.objects.create(evaluation=passee, etudiant=self.awa, valeur=D("12"))              # 1 note sur 2 eleves
        Evaluation.objects.create(annee_scolaire=self.annee, classe=self.af, matiere=self.maths, trimestre=2,
                                  libelle="Composition 2", date=self.aujourdhui + timedelta(days=5))
        e = self.donnees()["sections"]["evaluations"]
        self.assertEqual(e["trimestre"], 2)                                                     # debut_trimestre2 est passe
        self.assertEqual(e["notes_manquantes"], [{"classe": "6AF", "matiere": "Maths", "libelle": "Composition 1", "manquantes": 1}])
        self.assertEqual([p["libelle"] for p in e["prochaines"]], ["Composition 2"])
        self.assertEqual(e["resultats_a_valider"], [{"classe": "6AF", "trimestre": 2}])
        ValidationResultats.objects.create(classe=self.af, trimestre=2)
        e = self.donnees()["sections"]["evaluations"]
        self.assertEqual((e["resultats_a_valider"], e["bulletins_prets"]), ([], 1))


class EspaceProfesseurTests(BaseTableau):
    def setUp(self):
        super().setUp()
        self.compte = utilisateur(Role.PROFESSEUR, "prof_sy", professeur=self.sy)
        self.prof = client_de(self.compte)
        AffectationProfesseur.objects.create(professeur=self.sy, matiere=self.maths, classe=self.af, annee_scolaire=self.annee)

    def test_uniquement_ses_propres_donnees(self):
        # La seance a une date fixe dans le mois courant (le jour de `jours_avant` pourrait sinon tomber le mois precedent).
        a_lui = self.seance(heure=8, statut_professeur="EFFECTUE", date=self.aujourdhui.replace(day=1))
        self.seance(heure=9, prof=self.ba, statut_professeur="EFFECTUE", classe=self.d, date=self.aujourdhui.replace(day=1))   # a un autre
        espace = self.donnees(self.prof)["sections"]["mon_espace"]
        self.assertTrue(espace["fiche_liee"])
        self.assertEqual(a_lui.heures_effectuees, D("1.00"))
        self.assertEqual(espace["heures_du_mois"], "1.00")                          # uniquement les siennes
        self.assertEqual([h["classe"] for h in espace["historique_seances"]], ["6AF"])
        self.assertEqual(espace["mes_classes"], [{"classe": "6AF", "matiere": "Maths"}])
        self.assertEqual(espace["seances_a_valider"]["nombre"], 1)                  # sa seance, pas celle de Ba

    def test_prochains_cours_depuis_l_emploi_du_temps_publie(self):
        emploi = EmploiDuTemps.objects.create(annee_scolaire=self.annee, nom="Officiel", statut="PUBLIE", publie_le=timezone.now())
        salle = Salle.objects.create(nom="S1", capacite=40)
        for jour in range(7):
            SeanceProgrammee.objects.create(emploi=emploi, classe=self.af, matiere=self.maths, professeur=self.sy, salle=salle,
                                            jour=jour, heure_debut=time(23, 0), heure_fin=time(23, 59))
            SeanceProgrammee.objects.create(emploi=emploi, classe=self.d, matiere=self.maths, professeur=self.ba, salle=salle,
                                            jour=jour, heure_debut=time(22, 0), heure_fin=time(22, 59))
        cours = self.donnees(self.prof)["sections"]["mon_espace"]["prochains_cours"]
        self.assertEqual(len(cours), 6)
        self.assertTrue(all(c["classe"] == "6AF" and c["salle"] == "S1" for c in cours))          # jamais les cours de Ba
        self.assertEqual(cours, sorted(cours, key=lambda c: (c["date"], c["debut"])))

    def test_saisie_de_notes_limitee_a_ses_affectations(self):
        AffectationMatiereClasse.objects.create(matiere=self.maths, classe=self.af, coefficient=2)
        Evaluation.objects.create(annee_scolaire=self.annee, classe=self.af, matiere=self.maths, trimestre=2, libelle="Mon devoir")
        Evaluation.objects.create(annee_scolaire=self.annee, classe=self.d, matiere=self.maths, trimestre=2, libelle="Devoir d'un autre")
        notes = self.donnees(self.prof)["sections"]["mon_espace"]["saisie_notes"]
        self.assertEqual([n["libelle"] for n in notes], ["Mon devoir"])
        self.assertEqual(notes[0]["manquantes"], 2)

    def test_recap_de_remuneration_seulement_si_valide(self):
        self.seance(heure=8, statut_professeur="EFFECTUE")
        releve = remuneration.generer_releve(self.sy, self.aujourdhui - timedelta(days=1), self.admin)
        self.assertIsNone(self.donnees(self.prof)["sections"]["mon_espace"]["remuneration"])      # brouillon : invisible
        remuneration.valider_releve(releve, self.admin)
        r = self.donnees(self.prof)["sections"]["mon_espace"]["remuneration"]
        self.assertEqual((r["net"], r["paye"], r["solde"]), ("100.00", "0.00", "100.00"))

    def test_compte_sans_fiche_professeur(self):
        sans_fiche = client_de(utilisateur(Role.PROFESSEUR, "sans_fiche"))
        self.assertEqual(self.donnees(sans_fiche)["sections"]["mon_espace"], {"fiche_liee": False})


class RechercheGlobaleTests(BaseTableau):
    URL = "/api/tableau-de-bord/recherche/"

    def trouves(self, client, q):
        reponse = client.get(self.URL, {"q": q})
        self.assertEqual(reponse.status_code, 200)
        return [(r["type"], r["libelle"]) for r in reponse.json()["resultats"]]

    def test_recherche_transversale(self):
        self.assertEqual(self.trouves(self.client, "Diallo"), [("Etudiant", "Diallo Awa")])
        self.assertEqual(self.trouves(self.client, "E2"), [("Etudiant", "Ba Moussa")])
        self.assertIn(("Professeur", "Sy Oumar"), self.trouves(self.client, "Sy"))
        self.assertEqual(self.trouves(self.client, "6AF"), [("Classe", "6AF")])
        self.assertEqual(self.trouves(self.client, "Maths"), [("Matiere", "Maths")])
        self.assertEqual(self.trouves(self.client, "Awa Diallo"), [("Etudiant", "Diallo Awa")])     # plusieurs mots
        self.assertEqual(self.trouves(self.client, "zzzz"), [])
        self.assertEqual(self.trouves(self.client, "a"), [])                                          # 2 caracteres minimum

    def test_les_resultats_suivent_les_droits_du_role(self):
        comptable = client_de(utilisateur(Role.COMPTABLE, "compta"))          # pas de module etudiants ni classes
        self.assertEqual(self.trouves(comptable, "Diallo"), [])
        self.assertEqual(self.trouves(comptable, "6AF"), [])
        self.assertIn(("Professeur", "Sy Oumar"), self.trouves(comptable, "Sy"))                      # module professeurs
        professeur = client_de(utilisateur(Role.PROFESSEUR, "prof", professeur=self.sy))
        self.assertEqual(self.trouves(professeur, "Diallo"), [])
        self.assertEqual(self.trouves(professeur, "Sy"), [])
        self.assertEqual(APIClient().get(self.URL, {"q": "Diallo"}).status_code, 401)

    def test_limite_de_resultats_par_categorie(self):
        for i in range(12):
            self.eleve(f"Z{i}", f"Zorro{i}", "X", self.af)
        self.assertEqual(len(self.trouves(self.client, "Zorro")), 5)


class PerformanceTableauTests(BaseTableau):
    def test_nombre_de_requetes_borne_et_independant_du_volume(self):
        def mesurer():
            with CaptureQueriesContext(connection) as c:
                self.assertEqual(self.client.get(URL).status_code, 200)
            return len(c)
        self.seance(statut_professeur="EFFECTUE")
        avant = mesurer()
        for i in range(30):
            classe = Classe.objects.create(nom=f"C{i}", niveau=self.niveau, annee_scolaire=self.annee, capacite=40)
            self.eleve(f"Y{i}", f"N{i}", "P", classe)
            self.seance(heure=8, classe=classe, prof=self.ba, jours_avant=2 + i % 20, statut_professeur="EFFECTUE")
        self.assertEqual(mesurer(), avant)
        self.assertLess(avant, 60)
