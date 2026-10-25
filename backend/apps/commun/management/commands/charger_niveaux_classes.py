"""Insere les niveaux (Fondamental, College, Lycee) et leurs classes pour une annee scolaire.
Idempotent : peut etre relance sans creer de doublons (les elements existants sont conserves)."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import AnneeScolaire, Classe, Niveau

# (nom, code, ordre, classes)
NOMS_AR = {"FOND": "الأساسي", "COLL": "الإعدادي", "LYC": "الثانوي"}
NIVEAUX = [
    ("Fondamental", "FOND", 1, [f"{n}AF" for n in range(1, 7)]),
    ("College", "COLL", 2, [f"{n}AS" for n in range(1, 5)]),
    ("Lycee", "LYC", 3, [f"{n}{serie}" for n in (5, 6, 7) for serie in ("D", "C", "LM", "LO")]),
]


class Command(BaseCommand):
    help = "Insere les 3 niveaux (Fondamental, College, Lycee) et leurs classes pour l'annee scolaire choisie."

    def add_arguments(self, parser):
        parser.add_argument("--annee", help="Libelle de l'annee scolaire (ex: 2025-2026). Par defaut : l'annee active.")
        parser.add_argument("--capacite", type=int, default=40, help="Capacite des classes creees (defaut : 40).")

    def handle(self, *args, **options):
        annee = self.annee(options["annee"])
        niveaux_crees = classes_creees = 0
        with transaction.atomic():
            for nom, code, ordre, classes in NIVEAUX:
                niveau, cree = Niveau.objects.get_or_create(code=code, defaults={"nom": nom, "nom_ar": NOMS_AR.get(code, ""), "ordre": ordre})
                niveaux_crees += cree
                for nom_classe in classes:
                    _, cree = Classe.objects.get_or_create(
                        nom=nom_classe, annee_scolaire=annee,
                        defaults={"niveau": niveau, "capacite": options["capacite"]})
                    classes_creees += cree
        self.stdout.write(self.style.SUCCESS(
            f"Annee {annee.libelle} : {niveaux_crees} niveau(x) et {classes_creees} classe(s) cree(s)."))

    @staticmethod
    def annee(libelle):
        if libelle:
            try:
                return AnneeScolaire.objects.get(libelle=libelle)
            except AnneeScolaire.DoesNotExist:
                raise CommandError(f"Annee scolaire introuvable : {libelle}")
        annee = AnneeScolaire.objects.filter(active=True).first()
        if not annee:
            raise CommandError("Aucune annee scolaire active : creez-en une ou precisez --annee.")
        return annee
