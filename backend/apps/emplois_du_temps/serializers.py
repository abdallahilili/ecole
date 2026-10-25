from rest_framework import serializers

from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from . import services
from .conflits import minutes
from .donnees import _lire_hhmm
from .models import (
    ConfigurationHoraires, DisponibiliteProfesseur, EmploiDuTemps, IndisponibiliteSalle, SeanceProgrammee,
    StatutEmploi,
)


class ConfigurationHorairesSerializer(serializers.ModelSerializer):
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)

    class Meta:
        model = ConfigurationHoraires
        fields = "__all__"

    def validate_jours(self, valeur):
        try:
            jours = sorted({int(j) for j in valeur.split(",") if j.strip() != ""})
        except ValueError:
            raise ErreurMetier("Jours invalides (liste de 0 a 6 separes par des virgules).")
        if not jours or any(j < 0 or j > 6 for j in jours):
            raise ErreurMetier("Choisissez au moins un jour ouvrable (0 = lundi ... 6 = dimanche).")
        return ",".join(str(j) for j in jours)

    def validate(self, donnees):
        def val(nom):
            return donnees.get(nom, getattr(self.instance, nom, None))

        debut, fin, pas = minutes(val("heure_debut")), minutes(val("heure_fin")), val("duree_creneau")
        if fin <= debut:
            raise ErreurMetier("L'heure de fin de journee doit etre posterieure a l'heure de debut.")
        if pas <= 0 or (fin - debut) % pas:
            raise ErreurMetier("La plage horaire doit etre un multiple exact de la duree d'un creneau.")
        if val("duree_min_seance") <= 0 or val("duree_max_seance") < val("duree_min_seance"):
            raise ErreurMetier("Durees de seance invalides (minimum > 0 et maximum >= minimum).")
        if val("max_creneaux_jour_professeur") <= 0 or val("max_creneaux_consecutifs_professeur") <= 0:
            raise ErreurMetier("Les limites quotidiennes des professeurs doivent etre strictement positives.")
        pauses = val("pauses") or []
        for pause in pauses:
            try:
                a, b = _lire_hhmm(pause["debut"]), _lire_hhmm(pause["fin"])
            except (KeyError, ValueError, TypeError):
                raise ErreurMetier("Chaque pause doit avoir un 'debut' et une 'fin' au format HH:MM.")
            if not (debut <= a < b <= fin) or (a - debut) % pas or (b - a) % pas:
                raise ErreurMetier(
                    f"La pause {pause['debut']}-{pause['fin']} doit rester dans la journee et coincider avec la grille "
                    f"de creneaux de {pas} min."
                )
        return donnees


class _PlageSerializer(serializers.ModelSerializer):
    def validate(self, donnees):
        debut = donnees.get("heure_debut", getattr(self.instance, "heure_debut", None))
        fin = donnees.get("heure_fin", getattr(self.instance, "heure_fin", None))
        if fin <= debut:
            raise ErreurMetier("L'heure de fin doit etre posterieure a l'heure de debut.")
        return donnees


class DisponibiliteProfesseurSerializer(_PlageSerializer):
    professeur_nom = serializers.CharField(source="professeur.nom_complet", read_only=True)

    class Meta:
        model = DisponibiliteProfesseur
        fields = "__all__"

    def validate(self, donnees):
        utilisateur = self.context["request"].user
        if utilisateur.role == Role.PROFESSEUR:
            if utilisateur.professeur is None:
                raise ErreurMetier("Votre compte n'est relie a aucune fiche professeur.")
            donnees["professeur"] = utilisateur.professeur  # un professeur ne gere que ses propres disponibilites
        return super().validate(donnees)


class IndisponibiliteSalleSerializer(_PlageSerializer):
    salle_nom = serializers.CharField(source="salle.nom", read_only=True)

    class Meta:
        model = IndisponibiliteSalle
        fields = "__all__"


class EmploiDuTempsSerializer(serializers.ModelSerializer):
    annee_scolaire_libelle = serializers.CharField(source="annee_scolaire.libelle", read_only=True)
    nb_seances = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = EmploiDuTemps
        fields = "__all__"
        read_only_fields = ["statut", "origine", "rapport", "cree_par", "cree_le", "publie_le"]

    def validate(self, donnees):
        if self.instance:
            services.exiger_brouillon(self.instance)
            if "annee_scolaire" in donnees and donnees["annee_scolaire"] != self.instance.annee_scolaire:
                raise ErreurMetier("L'annee scolaire d'un emploi du temps ne peut pas etre modifiee.")
        return donnees


class SeanceProgrammeeSerializer(serializers.ModelSerializer):
    classe_nom = serializers.CharField(source="classe.nom", read_only=True)
    groupe_nom = serializers.CharField(source="groupe.nom", read_only=True, default=None)
    matiere_nom = serializers.CharField(source="matiere.nom_affiche", read_only=True)
    professeur_nom = serializers.CharField(source="professeur.nom_complet", read_only=True)
    salle_nom = serializers.CharField(source="salle.nom", read_only=True, default=None)

    class Meta:
        model = SeanceProgrammee
        fields = "__all__"

    def validate(self, donnees):
        instance = self.instance

        def val(nom):
            return donnees.get(nom, getattr(instance, nom, None))

        emploi = val("emploi")
        if instance and emploi != instance.emploi:
            raise ErreurMetier("Une seance ne peut pas changer d'emploi du temps.")
        services.exiger_brouillon(emploi)
        classe, groupe = val("classe"), val("groupe")
        if val("heure_fin") <= val("heure_debut"):
            raise ErreurMetier("L'heure de fin doit etre posterieure a l'heure de debut.")
        if classe.annee_scolaire_id != emploi.annee_scolaire_id:
            raise ErreurMetier("La classe choisie n'appartient pas a l'annee scolaire de cet emploi du temps.")
        if groupe and groupe.classe_id != classe.id:
            raise ErreurMetier("Le groupe choisi n'appartient pas a la classe selectionnee.")
        valeurs = {c: val(c) for c in ("classe", "groupe", "matiere", "professeur", "salle", "jour", "heure_debut", "heure_fin")}
        services.exiger_sans_conflit(services.conflits_pour(emploi, valeurs, exclure_pk=instance.pk if instance else None))
        return donnees
