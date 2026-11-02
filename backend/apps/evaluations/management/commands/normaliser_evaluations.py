"""Met les evaluations existantes au modele actuel : par matiere et trimestre, N devoirs (dont la moyenne donne
« Moy. interrogations », x3) et UNE composition (1ere x1, 2e x2, 3e x3).

Sans option, rien n'est modifie : la commande affiche seulement ce qu'elle ferait.
    --appliquer              execute les changements
    --supprimer-hors-modele  supprime aussi, avec leurs notes, les evaluations en trop (2e composition d'un meme trimestre,
                             devoir isole...) ; sans cette option elles sont seulement signalees.

Changements sans perte de notes (avec --appliquer) :
  - « Moy. interrogations » saisie directement -> devenue le « 1er devoir » (memes notes, meme moyenne) ;
  - composition unique d'un trimestre renommee et ponderee selon le trimestre (« 2e composition » x2 en T2...)."""

from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.evaluations import grille, services
from apps.evaluations.models import Evaluation, Note, TypeEvaluation, ValidationResultats


class Command(BaseCommand):
    help = "Aligne les evaluations existantes sur le modele : N devoirs + une composition par trimestre."

    def add_arguments(self, parser):
        parser.add_argument("--appliquer", action="store_true", help="Execute les changements (sinon simple simulation).")
        parser.add_argument("--supprimer-hors-modele", action="store_true", dest="supprimer",
                            help="Supprime aussi les evaluations en trop, avec leurs notes.")

    def handle(self, *args, **options):
        self.appliquer, self.supprimer = options["appliquer"], options["supprimer"]
        groupes = defaultdict(list)
        for e in Evaluation.objects.filter(parent__isnull=True).select_related("classe", "matiere").order_by("date", "id"):
            groupes[(e.classe_id, e.matiere_id, e.trimestre)].append(e)
        valides = set(ValidationResultats.objects.values_list("classe_id", "trimestre"))
        self.compteurs = defaultdict(int)
        for (classe_id, _matiere, trimestre), liste in sorted(groupes.items(), key=lambda g: (g[1][0].classe.nom, g[1][0].matiere.nom, g[0][2])):
            with transaction.atomic():
                self.traiter(liste, trimestre, (classe_id, trimestre) in valides)
        self.stdout.write("")
        if not self.compteurs:
            self.stdout.write(self.style.SUCCESS("Rien a faire : toutes les evaluations suivent deja le modele."))
            return
        resume = ", ".join(f"{n} {libelle}" for libelle, n in sorted(self.compteurs.items()))
        verbe = "Fait" if self.appliquer else "A faire (simulation)"
        self.stdout.write(self.style.WARNING(f"{verbe} : {resume}.") if not self.appliquer else self.style.SUCCESS(f"{verbe} : {resume}."))
        if not self.appliquer:
            self.stdout.write("Relancez avec --appliquer pour executer (et --supprimer-hors-modele pour supprimer les evaluations en trop).")

    def agir(self, evaluation, texte, cle, valide=False):
        marque = " [resultats valides : ils changeront]" if valide else ""
        self.stdout.write(f"{evaluation.classe.nom} / {evaluation.matiere.nom_affiche} / T{evaluation.trimestre} : {texte}{marque}")
        self.compteurs[cle] += 1

    def traiter(self, liste, trimestre, valide):
        interrogations = next((e for e in liste if e.type == TypeEvaluation.INTERROGATION), None)
        compositions = [e for e in liste if e.type == TypeEvaluation.EXAMEN]
        attendue = grille.LIBELLES_COMPOSITION[trimestre]
        retenue = next((e for e in compositions if e.libelle == attendue), compositions[0] if compositions else None)
        en_trop = [e for e in liste if e is not interrogations and e is not retenue]

        if interrogations is not None and not interrogations.devoirs.exists() and interrogations.notes.exists():
            self.agir(interrogations, f"« {interrogations.libelle} » saisie directement -> devient le 1er devoir", "moyenne(s) directe(s) convertie(s) en devoir", valide)
            if self.appliquer:
                self.convertir_en_devoir(interrogations)
        if retenue is not None and (retenue.libelle != attendue or retenue.poids != Decimal(trimestre)):
            self.agir(retenue, f"« {retenue.libelle} » (x{retenue.poids:g}) -> « {attendue} » (x{trimestre})", "composition(s) renommee(s)", valide)
            if self.appliquer:
                Evaluation.objects.filter(pk=retenue.pk).update(libelle=attendue, poids=Decimal(trimestre))
        for e in en_trop:
            nb = e.notes.count()
            if self.supprimer:
                self.agir(e, f"« {e.libelle} » en trop : supprimee avec ses {nb} note(s)", "evaluation(s) en trop supprimee(s)", valide)
                if self.appliquer:
                    e.delete()
            else:
                self.agir(e, f"« {e.libelle} » en trop ({nb} note(s)) : a supprimer avec --supprimer-hors-modele", "evaluation(s) en trop signalee(s)", valide)

    @staticmethod
    def convertir_en_devoir(interrogations):
        devoir = Evaluation.objects.create(
            annee_scolaire=interrogations.annee_scolaire, classe=interrogations.classe, matiere=interrogations.matiere,
            trimestre=interrogations.trimestre, libelle=grille.libelle_devoir(1), type=TypeEvaluation.DEVOIR,
            poids=Decimal(1), bareme=interrogations.bareme, parent=interrogations, date=interrogations.date,
        )
        notes = list(interrogations.notes.all())
        Note.objects.bulk_create([
            Note(evaluation=devoir, etudiant_id=n.etudiant_id, statut=n.statut, valeur=n.valeur, modifie_par=n.modifie_par) for n in notes
        ])
        services.recalculer_moyenne_interrogations(interrogations, [n.etudiant_id for n in notes])
