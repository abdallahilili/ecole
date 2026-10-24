from django.db import migrations, models


def champ_date(nom):
    return models.DateField(blank=True, db_column=nom, null=True)


class Migration(migrations.Migration):

    dependencies = [
        ("referentiels", "0001_initial"),
    ]

    operations = [
        # Semestres -> trimestres (ecole secondaire).
        migrations.RenameField(
            model_name="anneescolaire",
            old_name="debut_semestre2",
            new_name="debut_trimestre2",
        ),
        migrations.AlterField(
            model_name="anneescolaire",
            name="debut_trimestre2",
            field=champ_date("debut_trimestre2"),
        ),
        migrations.AddField(
            model_name="anneescolaire",
            name="debut_trimestre3",
            field=champ_date("debut_trimestre3"),
        ),
        # Periode d'evaluation unique -> un examen par trimestre.
        migrations.RenameField(
            model_name="anneescolaire",
            old_name="debut_evaluations",
            new_name="debut_examen1",
        ),
        migrations.AlterField(
            model_name="anneescolaire",
            name="debut_examen1",
            field=champ_date("debut_examen1"),
        ),
        migrations.RenameField(
            model_name="anneescolaire",
            old_name="fin_evaluations",
            new_name="fin_examen1",
        ),
        migrations.AlterField(
            model_name="anneescolaire",
            name="fin_examen1",
            field=champ_date("fin_examen1"),
        ),
        migrations.AddField(
            model_name="anneescolaire",
            name="debut_examen2",
            field=champ_date("debut_examen2"),
        ),
        migrations.AddField(
            model_name="anneescolaire",
            name="fin_examen2",
            field=champ_date("fin_examen2"),
        ),
        migrations.AddField(
            model_name="anneescolaire",
            name="debut_examen3",
            field=champ_date("debut_examen3"),
        ),
        migrations.AddField(
            model_name="anneescolaire",
            name="fin_examen3",
            field=champ_date("fin_examen3"),
        ),
    ]
