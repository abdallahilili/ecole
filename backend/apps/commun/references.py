from django.db import transaction
from django.utils import timezone
from .models import SequenceDocument


@transaction.atomic
def prochaine_reference(prefixe):
    annee = timezone.localdate().year
    sequence, _ = SequenceDocument.objects.select_for_update().get_or_create(prefixe=prefixe, annee=annee)
    sequence.dernier_numero += 1
    sequence.save(update_fields=["dernier_numero"])
    return f"{prefixe}-{annee}-{sequence.dernier_numero:05d}"
