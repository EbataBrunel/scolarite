# Generated by Django 5.0.7 on 2025-05-10 00:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('matiere', '0005_matiere_etablissement'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='matiere',
            name='etablissement',
        ),
    ]
