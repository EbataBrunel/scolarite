# Generated by Django 5.0.7 on 2025-04-22 14:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anneeacademique', '0004_anneecademique_status_cloture'),
        ('salle', '0004_alter_salle_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='salle',
            name='anneeacademique',
            field=models.ForeignKey(default=4, on_delete=django.db.models.deletion.CASCADE, to='anneeacademique.anneecademique'),
            preserve_default=False,
        ),
    ]
