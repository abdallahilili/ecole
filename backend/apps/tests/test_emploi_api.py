import io
from datetime import date, time

import openpyxl
from django.test import TestCase
from rest_framework.test import APIClient

from apps.commun.constantes import Role
from apps.commun.models import JournalAudit
from apps.emplois_du_temps.models import (
    DisponibiliteProfesseur, EmploiDuTemps, IndisponibiliteSalle, SeanceProgrammee, StatutEmploi,
)
from apps.etudiants.models import Etudiant, Inscription
from apps.presences.models import Seance
from apps.professeurs.models import AffectationProfesseur, Professeur
from apps.referentiels.models import AffectationMatiereClasse, AnneeScolaire, Classe, Groupe, Matiere, Niveau, Salle
from apps.utilisateurs.models import Utilisateur

BASE = "/api/emplois-du-temps/"


def utilisateur(role=Role.ADMINISTRATEUR, identifiant="admin", **extra):
    return Utilisateur.objects.create_user(identifiant=identifiant, mot_de_passe="secret123", nom="Test", role=role, **extra)


def client_de(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class BaseEmploi(TestCase):
    def setUp(self):
        self.annee = AnneeScolaire.objects.create(
            libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True,
            debut_vacances=date(2025, 12, 20), fin_vacances=date(2026, 1, 4))
        self.niveau = Niveau.objects.create(nom="6eme", code="6E", ordre=1)
        self.af = Classe.objects.create(nom="6AF", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        self.d = Classe.objects.create(nom="7D", niveau=self.niveau, annee_scolaire=self.annee, capacite=30)
        self.maths = Matiere.objects.create(nom="Maths", code="MATH")
        self.fr = Matiere.objects.create(nom="Francais", code="FR")
        self.sy = Professeur.objects.create(matricule="P1", nom="Sy", prenom="Oumar", tarif_horaire=100)
        self.ba = Professeur.objects.create(matricule="P2", nom="Ba", prenom="Cheikh", tarif_horaire=100)
        self.s1 = Salle.objects.create(nom="S1", capacite=40)
        self.s2 = Salle.objects.create(nom="S2", capacite=40)
        self.petite = Salle.objects.create(nom="Petite", capacite=1)
        for classe in (self.af, self.d):
            for matiere, seances, volume in ((self.maths, 3, 3), (self.fr, 2, 4)):    # maths 3 x 1 h ; francais 2 x 2 h
                AffectationMatiereClasse.objects.create(
                    matiere=matiere, classe=classe, coefficient=2, nombre_seances_semaine=seances, volume_horaire_hebdo=volume)
            AffectationProfesseur.objects.create(professeur=self.sy, matiere=self.maths, classe=classe, annee_scolaire=self.annee)
            AffectationProfesseur.objects.create(professeur=self.ba, matiere=self.fr, classe=classe, annee_scolaire=self.annee)
        for i in range(2):
            etudiant = Etudiant.objects.create(matricule=f"E{i}", nom=f"Nom{i}", prenom="X")
            Inscription.objects.create(etudiant=etudiant, annee_scolaire=self.annee, classe=self.af, date_inscription=date(2025, 9, 1))
        self.admin = utilisateur()
        self.client = client_de(self.admin)
        self.emploi = EmploiDuTemps.objects.create(annee_scolaire=self.annee, nom="Brouillon")

    def corps(self, **extra):
        donnees = {
            "emploi": self.emploi.id, "classe": self.af.id, "matiere": self.maths.id, "professeur": self.sy.id,
            "salle": self.s1.id, "jour": 0, "heure_debut": "08:00", "heure_fin": "09:00",
        }
        donnees.update(extra)
        return donnees

    def programmer(self, **extra):
        defauts = dict(emploi=self.emploi, classe=self.af, matiere=self.maths, professeur=self.sy, salle=self.s1,
                       jour=0, heure_debut=time(8, 0), heure_fin=time(9, 0))
        defauts.update(extra)
        return SeanceProgrammee.objects.create(**defauts)

    def generer(self, **extra):
        return self.client.post(BASE + "emplois/generer/", {"annee_scolaire": self.annee.id, "graine": 7, "temps_max": 10, **extra}, format="json")


class ConfigurationTests(BaseEmploi):
    def test_configuration_par_defaut_creee_a_la_demande(self):
        r = self.client.get(f"{BASE}configuration/annee/{self.annee.id}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()["jours"], r.json()["heure_debut"], r.json()["duree_creneau"]), ("0,1,2,3,4", "08:00:00", 60))

    def test_validation_de_la_configuration(self):
        config = self.client.get(f"{BASE}configuration/annee/{self.annee.id}/").json()
        url = f"{BASE}configuration/{config['id']}/"
        ok = self.client.patch(url, {"pauses": [{"debut": "10:00", "fin": "11:00"}]}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        for corps in (
            {"pauses": [{"debut": "10:15", "fin": "10:45"}]},        # pause hors grille
            {"pauses": [{"debut": "10:00"}]},                         # pause incomplete
            {"jours": "7"},                                            # jour inexistant
            {"jours": ""},
            {"heure_fin": "07:00"},
            {"duree_creneau": 50},                                     # la plage n'est pas un multiple
            {"duree_max_seance": 30},
        ):
            self.assertEqual(self.client.patch(url, corps, format="json").status_code, 400, corps)

    def test_ecriture_reservee_a_la_direction(self):
        config = self.client.get(f"{BASE}configuration/annee/{self.annee.id}/").json()
        pedago = client_de(utilisateur(Role.RESPONSABLE_PEDAGOGIQUE, "peda"))
        self.assertEqual(pedago.get(f"{BASE}configuration/").status_code, 200)
        self.assertEqual(pedago.patch(f"{BASE}configuration/{config['id']}/", {"duree_max_seance": 120}, format="json").status_code, 403)


class EditionManuelleTests(BaseEmploi):
    def test_creation_deplacement_copie_et_suppression_avec_historique(self):
        r = self.client.post(BASE + "seances/", self.corps())
        self.assertEqual(r.status_code, 201, r.content)
        identifiant = r.json()["id"]
        r = self.client.patch(f"{BASE}seances/{identifiant}/", {"jour": 1, "heure_debut": "09:00", "heure_fin": "10:00"})
        self.assertEqual(r.status_code, 200, r.content)
        audit = JournalAudit.objects.filter(action="MODIFICATION", modele="SeanceProgrammee").get()
        self.assertEqual((audit.ancienne_valeur["jour"], audit.nouvelle_valeur["jour"]), (0, 1))
        copie = self.client.post(f"{BASE}seances/{identifiant}/copier/", {"jour": 2, "heure_debut": "11:00"}, format="json")
        self.assertEqual(copie.status_code, 201, copie.content)
        self.assertEqual(copie.json()["heure_fin"], "12:00:00")                     # meme duree que l'original
        self.assertEqual(self.client.delete(f"{BASE}seances/{identifiant}/").status_code, 204)
        self.assertTrue(JournalAudit.objects.filter(action="SUPPRESSION", modele="SeanceProgrammee").exists())

    def test_conflits_refuses_avec_explication_structuree(self):
        self.programmer()
        # Meme professeur, meme creneau, autre classe et autre salle.
        r = self.client.post(BASE + "seances/", self.corps(classe=self.d.id, salle=self.s2.id))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "conflit")
        self.assertEqual([c["type"] for c in r.json()["conflits"]], ["PROFESSEUR_SIMULTANE"])
        self.assertIn("Sy Oumar", r.json()["detail"])
        # Meme classe en meme temps (autre professeur, autre salle).
        r = self.client.post(BASE + "seances/", self.corps(matiere=self.fr.id, professeur=self.ba.id, salle=self.s2.id))
        self.assertEqual([c["type"] for c in r.json()["conflits"]], ["CLASSE_SIMULTANEE"])
        # Meme salle.
        r = self.client.post(BASE + "seances/", self.corps(classe=self.d.id, matiere=self.fr.id, professeur=self.ba.id))
        self.assertEqual([c["type"] for c in r.json()["conflits"]], ["SALLE_SIMULTANEE"])
        self.assertEqual(SeanceProgrammee.objects.count(), 1)

    def test_un_deplacement_qui_cree_un_conflit_est_refuse_et_la_seance_reste_en_place(self):
        a = self.programmer()
        b = self.programmer(classe=self.d, salle=self.s2, jour=1)
        r = self.client.patch(f"{BASE}seances/{b.id}/", {"jour": 0})              # Sy serait deja occupe lundi 8h
        self.assertEqual(r.status_code, 400)
        b.refresh_from_db()
        self.assertEqual(b.jour, 1)
        # Se deplacer sur son propre creneau n'est pas un conflit avec soi-meme.
        self.assertEqual(self.client.patch(f"{BASE}seances/{a.id}/", {"salle": self.s2.id}).status_code, 200)

    def test_contraintes_de_disponibilite_horaires_capacite_et_affectation(self):
        DisponibiliteProfesseur.objects.create(professeur=self.sy, jour=2, heure_debut=time(8), heure_fin=time(10), type="INDISPONIBLE")
        IndisponibiliteSalle.objects.create(salle=self.s2, jour=3, heure_debut=time(8), heure_fin=time(14), motif="Travaux")
        config = self.client.get(f"{BASE}configuration/annee/{self.annee.id}/").json()
        self.client.patch(f"{BASE}configuration/{config['id']}/", {"pauses": [{"debut": "10:00", "fin": "11:00"}]}, format="json")
        def type_conflit(**extra):
            r = self.client.post(BASE + "seances/", self.corps(**extra))
            return [c["type"] for c in r.json().get("conflits", [])] or r.status_code
        self.assertEqual(type_conflit(jour=2), ["PROFESSEUR_INDISPONIBLE"])
        self.assertEqual(type_conflit(jour=3, salle=self.s2.id), ["SALLE_INDISPONIBLE"])
        self.assertEqual(type_conflit(jour=5), ["HORS_HORAIRES"])                      # samedi
        self.assertEqual(type_conflit(heure_debut="10:00", heure_fin="11:00"), ["HORS_HORAIRES"])  # pause
        self.assertEqual(sorted(type_conflit(heure_debut="11:00", heure_fin="15:00")), ["DUREE", "HORS_HORAIRES"])
        self.assertEqual(type_conflit(salle=self.petite.id), ["CAPACITE_SALLE"])       # 2 eleves > 1 place
        self.assertEqual(type_conflit(professeur=self.ba.id), ["PROFESSEUR_NON_AFFECTE"])
        self.assertEqual(SeanceProgrammee.objects.count(), 0)

    def test_groupe_hors_classe_ou_heures_inversees_refuses(self):
        autre = Groupe.objects.create(nom="G1", classe=self.d)
        self.assertEqual(self.client.post(BASE + "seances/", self.corps(groupe=autre.id)).status_code, 400)
        self.assertEqual(self.client.post(BASE + "seances/", self.corps(heure_debut="09:00", heure_fin="08:00")).status_code, 400)

    def test_emploi_publie_ou_archive_non_modifiable(self):
        self.programmer()
        self.assertEqual(self.client.post(f"{BASE}emplois/{self.emploi.id}/publier/", {}, format="json").status_code, 200)
        r = self.client.post(BASE + "seances/", self.corps(jour=1))
        self.assertEqual(r.status_code, 400)
        self.assertIn("dupliquez", r.json()["detail"])
        self.assertEqual(self.client.delete(f"{BASE}emplois/{self.emploi.id}/").status_code, 400)
        self.assertEqual(self.client.patch(f"{BASE}emplois/{self.emploi.id}/", {"nom": "x"}).status_code, 400)
        copie = self.client.post(f"{BASE}emplois/{self.emploi.id}/dupliquer/", {}, format="json")
        self.assertEqual(copie.status_code, 201)
        self.assertEqual((copie.json()["statut"], copie.json()["nb_seances"]), ("BROUILLON", 1))


class GenerationTests(BaseEmploi):
    def test_generation_sans_conflit_et_conforme_aux_besoins(self):
        r = self.generer()
        self.assertEqual(r.status_code, 201, r.content)
        emploi = r.json()
        rapport = emploi["rapport"]
        # 2 classes x (3 seances de maths + 2 de francais) = 10 seances, francais sur 2 creneaux.
        self.assertEqual((emploi["origine"], emploi["statut"], emploi["nb_seances"]), ("GENETIQUE", "BROUILLON", 10))
        self.assertEqual((rapport["unites"], rapport["violations"], rapport["publiable"], rapport["conflits"]), (10, 0, True, []))
        verification = self.client.get(f"{BASE}emplois/{emploi['id']}/verifier/", {"publication": 1}).json()
        self.assertEqual((verification["valide"], verification["nb_conflits"]), (True, 0))
        seances = SeanceProgrammee.objects.filter(emploi_id=emploi["id"])
        self.assertEqual(sorted(len(list(seances.filter(classe=c, matiere=self.maths))) for c in (self.af, self.d)), [3, 3])
        for s in seances.filter(matiere=self.fr):
            self.assertEqual((s.heure_fin.hour - s.heure_debut.hour), 2)
        self.assertTrue(all(s.salle_id for s in seances))

    def test_generation_reproductible_avec_la_meme_graine(self):
        a, b = self.generer(generations=20).json(), self.generer(generations=20).json()
        def contenu(id_):
            return sorted(SeanceProgrammee.objects.filter(emploi_id=id_).values_list(
                "classe_id", "matiere_id", "jour", "heure_debut", "salle_id"))
        self.assertEqual(contenu(a["id"]), contenu(b["id"]))

    def test_les_indisponibilites_sont_respectees_par_la_generation(self):
        for jour in (0, 1, 2):
            DisponibiliteProfesseur.objects.create(professeur=self.sy, jour=jour, heure_debut=time(8), heure_fin=time(14), type="INDISPONIBLE")
        emploi = self.generer().json()
        jours = set(SeanceProgrammee.objects.filter(emploi_id=emploi["id"], professeur=self.sy).values_list("jour", flat=True))
        self.assertTrue(jours <= {3, 4}, jours)
        self.assertTrue(emploi["rapport"]["publiable"])

    def test_ressources_insuffisantes_signalees_et_publication_refusee(self):
        # Sy n'est disponible que 2 jours (10 creneaux) mais doit assurer 6 creneaux de maths : possible ;
        # on le rend indisponible presque toute la semaine -> impossible.
        for jour in range(5):
            DisponibiliteProfesseur.objects.create(professeur=self.sy, jour=jour, heure_debut=time(8), heure_fin=time(13), type="INDISPONIBLE")
        r = self.generer()
        self.assertEqual(r.status_code, 201)
        rapport = r.json()["rapport"]
        self.assertFalse(rapport["publiable"])
        self.assertTrue(any("Sy Oumar" in d and "creneaux" in d for d in rapport["diagnostics"]), rapport["diagnostics"])
        self.assertGreater(len(rapport["conflits"]), 0)
        refus = self.client.post(f"{BASE}emplois/{r.json()['id']}/publier/", {}, format="json")
        self.assertEqual(refus.status_code, 400)
        self.assertEqual(refus.json()["code"], "conflit")
        self.assertEqual(EmploiDuTemps.objects.get(pk=r.json()["id"]).statut, StatutEmploi.BROUILLON)

    def test_aucune_seance_a_programmer_diagnostique(self):
        AffectationProfesseur.objects.all().delete()
        r = self.generer()
        self.assertEqual(r.status_code, 400)
        self.assertIn("Aucune seance a programmer", r.json()["detail"])

    def test_matiere_sans_volume_horaire_diagnostiquee(self):
        AffectationMatiereClasse.objects.filter(matiere=self.fr).update(nombre_seances_semaine=0)
        rapport = self.generer().json()["rapport"]
        self.assertEqual(rapport["unites"], 6)
        self.assertTrue(any("Francais" in d and "non defini" in d for d in rapport["diagnostics"]))

    def test_generation_reservee_a_la_gestion(self):
        r = client_de(utilisateur(Role.COMPTABLE, "compta")).post(BASE + "emplois/generer/", {"annee_scolaire": self.annee.id}, format="json")
        self.assertEqual(r.status_code, 403)


class PublicationEtVersionsTests(BaseEmploi):
    def test_publication_versions_et_archivage(self):
        self.programmer()
        premier = self.client.post(f"{BASE}emplois/{self.emploi.id}/publier/", {"commentaire": "Rentree"}, format="json")
        self.assertEqual((premier.status_code, premier.json()["version"]), (200, 1))
        copie = self.client.post(f"{BASE}emplois/{self.emploi.id}/dupliquer/", {"nom": "Rentree v2"}, format="json").json()
        SeanceProgrammee.objects.create(emploi_id=copie["id"], classe=self.af, matiere=self.fr, professeur=self.ba, salle=self.s1,
                                        jour=1, heure_debut=time(8), heure_fin=time(10))
        self.assertEqual(self.client.post(f"{BASE}emplois/{copie['id']}/publier/", {}, format="json").json()["version"], 2)
        self.emploi.refresh_from_db()
        self.assertEqual(self.emploi.statut, StatutEmploi.ARCHIVE)               # un seul emploi publie par annee
        self.assertEqual(EmploiDuTemps.objects.filter(statut=StatutEmploi.PUBLIE).count(), 1)
        versions = self.client.get(BASE + "emplois/versions/", {"annee_scolaire": self.annee.id}).json()
        self.assertEqual([(v["numero"], v["nb_seances"]) for v in versions], [(2, 2), (1, 1)])
        self.assertEqual(versions[1]["commentaire"], "Rentree")
        self.assertTrue(JournalAudit.objects.filter(action="PUBLICATION").count() == 2)

    def test_publication_refusee_si_vide_ou_en_conflit_ou_sans_salle(self):
        self.assertEqual(self.client.post(f"{BASE}emplois/{self.emploi.id}/publier/", {}, format="json").status_code, 400)
        self.programmer(salle=None)
        r = self.client.post(f"{BASE}emplois/{self.emploi.id}/publier/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual([c["type"] for c in r.json()["conflits"]], ["SALLE_MANQUANTE"])

    def test_generation_des_seances_de_presence_sans_doublon_et_hors_vacances(self):
        self.programmer()                                                          # lundi 8h-9h, maths, 6AF
        self.client.post(f"{BASE}emplois/{self.emploi.id}/publier/", {}, format="json")
        corps = {"du": "2025-12-15", "au": "2026-01-12"}
        r = self.client.post(f"{BASE}emplois/{self.emploi.id}/generer-seances/", corps, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        dates = sorted(Seance.objects.values_list("date", flat=True))
        # Lundis : 15/12, (22/12 et 29/12 en vacances), 05/01, 12/01.
        self.assertEqual(dates, [date(2025, 12, 15), date(2026, 1, 5), date(2026, 1, 12)])
        self.assertEqual(Seance.objects.first().professeur, self.sy)
        r = self.client.post(f"{BASE}emplois/{self.emploi.id}/generer-seances/", corps, format="json")
        self.assertEqual((r.json()["creees"], r.json()["ignorees"]), (0, 3))
        self.assertEqual(Seance.objects.count(), 3)

    def test_generation_des_seances_exige_un_emploi_publie_et_des_dates_valides(self):
        self.programmer()
        url = f"{BASE}emplois/{self.emploi.id}/generer-seances/"
        self.assertEqual(self.client.post(url, {"du": "2025-10-01", "au": "2025-10-31"}, format="json").status_code, 400)
        self.client.post(f"{BASE}emplois/{self.emploi.id}/publier/", {}, format="json")
        self.assertEqual(self.client.post(url, {"du": "2025-10-31", "au": "2025-10-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"du": "2027-01-01", "au": "2027-02-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"du": "pas une date", "au": "2025-10-01"}, format="json").status_code, 400)


class ConsultationEtExportsTests(BaseEmploi):
    def setUp(self):
        super().setUp()
        self.programmer()
        self.programmer(classe=self.d, matiere=self.fr, professeur=self.ba, salle=self.s2, jour=1, heure_debut=time(8), heure_fin=time(10))
        self.url = f"{BASE}emplois/{self.emploi.id}/"

    def test_vue_filtree_par_classe_professeur_salle(self):
        complet = self.client.get(self.url + "vue/").json()
        self.assertEqual(len(complet["seances"]), 2)
        self.assertEqual([j["nom"] for j in complet["cadre"]["jours"]], ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"])
        self.assertEqual(len(complet["cadre"]["creneaux"]), 6)
        self.assertFalse(any(c["pause"] for c in complet["cadre"]["creneaux"]))              # pas de pause par defaut
        config = self.client.get(f"{BASE}configuration/annee/{self.annee.id}/").json()
        self.client.patch(f"{BASE}configuration/{config['id']}/", {"pauses": [{"debut": "10:00", "fin": "11:00"}]}, format="json")
        creneaux = self.client.get(self.url + "vue/").json()["cadre"]["creneaux"]
        self.assertEqual([c["pause"] for c in creneaux], [False, False, True, False, False, False])
        self.assertEqual([s["classe_nom"] for s in self.client.get(self.url + "vue/", {"classe": self.d.id}).json()["seances"]], ["7D"])
        self.assertEqual([s["professeur_nom"] for s in self.client.get(self.url + "vue/", {"professeur": self.sy.id}).json()["seances"]], ["Sy Oumar"])
        self.assertEqual(len(self.client.get(self.url + "vue/", {"salle": self.s2.id}).json()["seances"]), 1)

    def test_les_conflits_sont_signales_dans_la_vue(self):
        self.programmer(classe=self.d, salle=self.s2)                              # Sy double-reserve lundi 8h
        seances = self.client.get(self.url + "vue/").json()
        self.assertEqual(seances["nb_conflits"], 1)
        self.assertEqual(len([s for s in seances["seances"] if s["conflits"]]), 2)

    def test_exports_pdf_et_excel(self):
        pdf = self.client.get(self.url + "pdf/", {"classe": self.af.id})
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        toutes = self.client.get(self.url + "pdf/", {"toutes": "classe"})
        self.assertGreater(len(toutes.content), len(pdf.content) // 2)
        classeur = openpyxl.load_workbook(io.BytesIO(self.client.get(self.url + "excel/", {"toutes": "classe"}).content))
        self.assertEqual(sorted(classeur.sheetnames), ["Classe 6AF", "Classe 7D"])
        valeurs = [c.value for ligne in classeur["Classe 6AF"].iter_rows() for c in ligne if c.value]
        self.assertTrue(any("Maths" in str(v) for v in valeurs))

    def test_professeur_ne_voit_que_l_emploi_publie_et_sa_propre_grille(self):
        compte = utilisateur(Role.PROFESSEUR, "prof", professeur=self.sy)
        prof = client_de(compte)
        self.assertEqual(prof.get(BASE + "emplois/").json()["total"], 0)           # brouillon invisible
        self.assertEqual(prof.get(self.url + "vue/").status_code, 404)
        self.client.post(self.url + "publier/", {}, format="json")
        self.assertEqual(prof.get(BASE + "emplois/").json()["total"], 1)
        vue = prof.get(self.url + "vue/", {"professeur": self.ba.id, "classe": self.d.id}).json()   # tentative de voir autrui
        self.assertEqual({s["professeur_nom"] for s in vue["seances"]}, {"Sy Oumar"})
        self.assertEqual(prof.post(self.url + "dupliquer/", {}, format="json").status_code, 403)
        self.assertEqual(prof.get(BASE + "seances/").status_code, 403)

    def test_disponibilites_un_professeur_ne_gere_que_les_siennes(self):
        prof = client_de(utilisateur(Role.PROFESSEUR, "prof", professeur=self.sy))
        DisponibiliteProfesseur.objects.create(professeur=self.ba, jour=1, heure_debut=time(8), heure_fin=time(9))
        r = prof.post(BASE + "disponibilites-professeurs/", {"professeur": self.ba.id, "jour": 0, "heure_debut": "08:00",
                                                           "heure_fin": "10:00", "type": "INDISPONIBLE"})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(DisponibiliteProfesseur.objects.get(pk=r.json()["id"]).professeur, self.sy)   # force a son propre compte
        liste = prof.get(BASE + "disponibilites-professeurs/").json()["resultats"]
        self.assertEqual({d["professeur"] for d in liste}, {self.sy.id})
        autre = DisponibiliteProfesseur.objects.get(professeur=self.ba)
        self.assertEqual(prof.delete(f"{BASE}disponibilites-professeurs/{autre.id}/").status_code, 404)
        self.assertEqual(prof.post(BASE + "disponibilites-professeurs/", {"professeur": self.sy.id, "jour": 0, "heure_debut": "10:00",
                                                                          "heure_fin": "09:00"}).status_code, 400)
