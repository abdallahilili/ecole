from django.core.management.base import BaseCommand

from apps.etudiants.models import Inscription
from apps.scolarite import services


class Command(BaseCommand):
    help = (
        "Cree la fiche de paiement (un mois a payer par echeance, octobre -> juillet) des inscriptions actives qui n'en "
        "ont pas, et ajoute les mois manquants aux fiches existantes (ex. juillet). Les mois deja payes ne changent pas. "
        "La mensualite est celle de l'inscription, sinon le tarif de la classe ; sans tarif, l'inscription est ignoree "
        "(la fiche se genere ensuite depuis la page de l'etudiant). Peut etre relancee sans risque."
    )

    def handle(self, *args, **options):
        creees = completees = sans_tarif = 0
        for inscription in Inscription.objects.filter(statut="ACTIVE").select_related("classe", "annee_scolaire"):
            avait_une_fiche = inscription.echeances.exists()
            ajoutes = services.generer_echeances(inscription)
            if ajoutes is None:
                sans_tarif += 1
            elif ajoutes and avait_une_fiche:
                completees += 1
            elif ajoutes:
                creees += 1
        self.stdout.write(self.style.SUCCESS(f"{creees} fiche(s) de paiement creee(s), {completees} fiche(s) completee(s) (mois ajoutes)."))
        if sans_tarif:
            self.stdout.write(self.style.WARNING(f"{sans_tarif} inscription(s) ignoree(s) : aucun tarif defini pour leur classe."))
