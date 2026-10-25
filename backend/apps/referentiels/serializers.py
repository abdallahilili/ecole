from rest_framework import serializers
from apps.commun.exceptions import ErreurMetier
from .models import AnneeScolaire, Niveau, Salle, Classe, TarifClasse, Groupe, Matiere, AffectationMatiereClasse


class AnneeScolaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnneeScolaire
        fields = "__all__"
        read_only_fields = ("archivee", "date_archivage")   # modifies uniquement par l'archivage (suppression)

    def validate(self, donnees):
        debut = donnees.get("date_debut", getattr(self.instance, "date_debut", None))
        fin = donnees.get("date_fin", getattr(self.instance, "date_fin", None))
        if debut and fin and fin <= debut:
            raise ErreurMetier("La date de fin doit etre posterieure a la date de debut.")

        def valeur(nom):
            return donnees.get(nom, getattr(self.instance, nom, None))

        # Les trimestres se suivent : debut < 2e trimestre < 3e trimestre < fin.
        jalons = [
            ("la date de debut", debut),
            ("le debut du 2e trimestre", valeur("debut_trimestre2")),
            ("le debut du 3e trimestre", valeur("debut_trimestre3")),
            ("la date de fin", fin),
        ]
        jalons = [(nom, d) for nom, d in jalons if d]
        for (nom_prec, d_prec), (nom_suiv, d_suiv) in zip(jalons, jalons[1:]):
            if d_suiv <= d_prec:
                raise ErreurMetier(f"{nom_suiv.capitalize()} doit etre posterieur(e) a {nom_prec}.")

        for suffixe in ("", "2"):
            debut_vac, fin_vac = valeur(f"debut_vacances{suffixe}"), valeur(f"fin_vacances{suffixe}")
            if debut_vac and fin_vac and fin_vac < debut_vac:
                raise ErreurMetier(f"La fin des vacances {suffixe or 1} ne peut pas preceder leur debut.")
        vacances = [(d, f) for d, f in ((valeur("debut_vacances"), valeur("fin_vacances")),
                                        (valeur("debut_vacances2"), valeur("fin_vacances2"))) if d and f]
        if len(vacances) == 2 and vacances[1][0] <= vacances[0][1]:
            raise ErreurMetier("Les vacances 2 doivent commencer apres la fin des vacances 1.")

        for n in (1, 2, 3):
            debut_exam, fin_exam = valeur(f"debut_examen{n}"), valeur(f"fin_examen{n}")
            if debut_exam and fin_exam and fin_exam < debut_exam:
                raise ErreurMetier(f"La fin de l'examen {n} ne peut pas preceder son debut.")
        return donnees

    def validate_cloturee(self, valeur):
        if self.instance and self.instance.cloturee and not valeur:
            raise ErreurMetier("Une annee scolaire cloturee ne peut pas etre reouverte.")
        return valeur


class NiveauSerializer(serializers.ModelSerializer):
    nom_affiche = serializers.CharField(read_only=True)

    class Meta:
        model = Niveau
        fields = "__all__"


class SalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Salle
        fields = "__all__"


class ClasseSerializer(serializers.ModelSerializer):
    niveau_nom = serializers.CharField(source="niveau.nom_affiche", read_only=True)
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)
    effectif = serializers.SerializerMethodField()

    class Meta:
        model = Classe
        fields = "__all__"

    def get_effectif(self, obj):
        # Nombre d'inscriptions actives (annotation de la vue ; requete directe sinon).
        if hasattr(obj, "effectif_actif"):
            return obj.effectif_actif
        if hasattr(obj, "inscriptions"):
            return obj.inscriptions.filter(statut="ACTIVE").count()
        return 0

    def validate(self, donnees):
        capacite = donnees.get("capacite", getattr(self.instance, "capacite", None))
        salle = donnees.get("salle_principale", getattr(self.instance, "salle_principale", None))
        if salle and capacite and salle.capacite and capacite > salle.capacite:
            raise ErreurMetier(
                f"La capacite de la classe ({capacite}) depasse celle de la salle '{salle.nom}' ({salle.capacite})."
            )
        return donnees


class TarifClasseSerializer(serializers.ModelSerializer):
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    niveau_nom = serializers.CharField(source="classe.niveau.nom_affiche", read_only=True)
    annee_scolaire_libelle = serializers.CharField(source="classe.annee_scolaire.libelle", read_only=True)

    class Meta:
        model = TarifClasse
        fields = "__all__"

    def validate_montant(self, valeur):
        if valeur <= 0:
            raise ErreurMetier("Le montant du tarif doit etre strictement positif.")
        return valeur


class GroupeSerializer(serializers.ModelSerializer):
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)

    class Meta:
        model = Groupe
        fields = "__all__"


class MatiereSerializer(serializers.ModelSerializer):
    nom_affiche = serializers.CharField(read_only=True)

    class Meta:
        model = Matiere
        fields = "__all__"


class AffectationMatiereClasseSerializer(serializers.ModelSerializer):
    matiere_nom = serializers.CharField(source="matiere.nom_affiche", read_only=True)
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)

    class Meta:
        model = AffectationMatiereClasse
        fields = "__all__"

    def validate_coefficient(self, valeur):
        if valeur <= 0:
            raise ErreurMetier("Le coefficient doit etre strictement positif.")
        return valeur

    def validate_volume_horaire_hebdo(self, valeur):
        if valeur <= 0:
            raise ErreurMetier("Le volume horaire hebdomadaire doit etre strictement positif.")
        return valeur
