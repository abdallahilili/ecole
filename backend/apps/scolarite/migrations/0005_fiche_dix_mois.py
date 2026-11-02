from django.db import migrations, models


def grilles_a_dix_mois(apps, schema_editor):
    """L'annee de paiement va d'octobre a juillet (10 mois) : les grilles restees sur l'ancien defaut de 9 mois suivent."""
    apps.get_model("scolarite", "GrilleFrais").objects.filter(nombre_mois=9).update(nombre_mois=10)


class Migration(migrations.Migration):

    dependencies = [
        ('scolarite', '0004_montant_mensuel_echeances'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grillefrais',
            name='nombre_mois',
            field=models.IntegerField(db_column='nombre_mois', default=10),
        ),
        migrations.RunPython(grilles_a_dix_mois, migrations.RunPython.noop),
    ]
