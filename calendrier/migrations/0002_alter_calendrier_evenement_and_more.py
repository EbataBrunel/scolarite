# Generated by Django 5.0.7 on 2025-03-14 14:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendrier', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calendrier',
            name='evenement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evenements', to='calendrier.evenementscolaire'),
        ),
        migrations.AlterField(
            model_name='calendrier',
            name='trimestre',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trimestres', to='calendrier.trimestre'),
        ),
    ]
