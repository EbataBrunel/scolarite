# Generated by Django 5.0.7 on 2025-05-21 17:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('renumeration', '0009_contrat_admin_contrat_date_signature_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='renumeration',
            name='mode_payment',
            field=models.CharField(choices=[('Espèce', 'Espèce'), ('Virement', 'Virement'), ('Mobile', 'Mobile')], default='Espèce', max_length=20),
        ),
        migrations.AddField(
            model_name='renumerationadmin',
            name='mode_payment',
            field=models.CharField(choices=[('Espèce', 'Espèce'), ('Virement', 'Virement'), ('Mobile', 'Mobile')], default='Espèce', max_length=20),
        ),
    ]
