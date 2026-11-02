from django.db import migrations, models


def numeroter_inscriptions_existantes(apps, schema_editor):
    """Chaque annee reprend ses inscriptions dans l'ordre (date d'inscription, creation) : E001, E002..."""
    Inscription = apps.get_model("etudiants", "Inscription")
    annees = Inscription.objects.order_by().values_list("annee_scolaire_id", flat=True).distinct()
    for annee in annees:
        inscriptions = Inscription.objects.filter(annee_scolaire_id=annee).order_by("date_inscription", "id")
        for rang, inscription in enumerate(inscriptions, start=1):
            inscription.numero_inscription = f"E{rang:03d}"
            inscription.save(update_fields=["numero_inscription"])


class Migration(migrations.Migration):

    dependencies = [
        ('etudiants', '0003_montant_mensuel_echeances'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscription',
            name='numero_inscription',
            field=models.CharField(blank=True, db_column='numero_inscription', default='', max_length=20),
        ),
        migrations.RunPython(numeroter_inscriptions_existantes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='inscription',
            constraint=models.UniqueConstraint(fields=('annee_scolaire', 'numero_inscription'), name='inscription_numero_unique'),
        ),
    ]
