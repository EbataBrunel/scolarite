# Generated by Django 5.0.7 on 2025-07-08 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emargement', '0003_alter_emargement_matiere'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emargement',
            name='seance',
            field=models.CharField(blank=True, choices=[('Cours', 'Cours'), ('Travail Dirigé', 'Travail Dirigé'), ('Contrôle', 'Contrôle'), ('Travail Pratique', 'Travail Pratique')], max_length=300, null=True),
        ),
        migrations.AlterField(
            model_name='emargement',
            name='titre',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
