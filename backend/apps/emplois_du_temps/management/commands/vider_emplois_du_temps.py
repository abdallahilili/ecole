"""Vide tout ce qui concerne la planification des horaires, pour repartir de zero classe par classe.

Supprime : les emplois du temps (brouillons, publies, archives) avec leurs seances programmees, les versions
publiees, les disponibilites saisies pour les professeurs et les indisponibilites de salles.
Ne touche PAS : le cadre horaire de chaque annee, les professeurs, les affectations professeur-matiere-classe, les
matieres et leurs volumes horaires, ni les seances de presence deja creees (listes d'appel, absences).

Sans `--confirmer`, la commande se contente d'afficher ce qui serait supprime."""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.commun.audit import enregistrer_audit
from apps.emplois_du_temps.models import (
    DisponibiliteProfesseur, EmploiDuTemps, IndisponibiliteSalle, SeanceProgrammee, VersionEmploiDuTemps,
)


class Command(BaseCommand):
    help = "Vide les emplois du temps, leurs versions et les disponibilites (apercu sans --confirmer)."

    def add_arguments(self, parser):
        parser.add_argument("--confirmer", action="store_true", help="Supprime reellement les donnees (sinon : apercu).")

    def handle(self, *args, confirmer=False, **options):
        # Ordre de suppression : les versions protegent leur emploi, qui emporte ses seances.
        cibles = [
            ("Versions publiees", VersionEmploiDuTemps), ("Seances programmees", SeanceProgrammee),
            ("Emplois du temps", EmploiDuTemps), ("Disponibilites des professeurs", DisponibiliteProfesseur),
            ("Indisponibilites des salles", IndisponibiliteSalle),
        ]
        comptes = {nom: modele.objects.count() for nom, modele in cibles}
        for nom, nombre in comptes.items():
            self.stdout.write(f"  {nom} : {nombre}")
        if not confirmer:
            self.stdout.write("Apercu seulement : relancez avec --confirmer pour supprimer.")
            return
        with transaction.atomic():
            for nom, modele in cibles:
                modele.objects.all().delete()
            enregistrer_audit(None, "SUPPRESSION", "EmploiDuTemps", "tous", ancienne_valeur=comptes)
        self.stdout.write(self.style.SUCCESS("Emplois du temps et disponibilites supprimes."))
