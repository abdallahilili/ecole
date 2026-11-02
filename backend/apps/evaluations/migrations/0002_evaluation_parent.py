import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluation',
            name='parent',
            field=models.ForeignKey(blank=True, db_column='id_parent', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='devoirs', to='evaluations.evaluation'),
        ),
    ]
