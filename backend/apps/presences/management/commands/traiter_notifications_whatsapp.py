import time

from django.core.management.base import BaseCommand

from apps.presences import whatsapp


class Command(BaseCommand):
    help = (
        "Envoie les notifications WhatsApp en attente (file d'attente) avec nouvelles tentatives. "
        "A planifier (cron / Planificateur de taches) ou a lancer avec --boucle."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=50, help="Nombre maximal de messages par passage.")
        parser.add_argument("--boucle", action="store_true", help="Repete le traitement indefiniment.")
        parser.add_argument("--intervalle", type=int, default=60, help="Secondes entre deux passages (avec --boucle).")

    def handle(self, *args, **options):
        if not whatsapp.api_configuree():
            self.stdout.write(self.style.WARNING(
                "API WhatsApp non configuree (WHATSAPP_JETON, WHATSAPP_ID_NUMERO, WHATSAPP_MODELE) : "
                "les notifications restent en attente et peuvent etre envoyees via wa.me."
            ))
            return
        while True:
            bilan = whatsapp.traiter_file(limite=options["limite"])
            self.stdout.write(
                f"envoyees={bilan['envoyees']} reportees={bilan['reportees']} echecs={bilan['echecs']}"
            )
            if not options["boucle"]:
                return
            time.sleep(options["intervalle"])
