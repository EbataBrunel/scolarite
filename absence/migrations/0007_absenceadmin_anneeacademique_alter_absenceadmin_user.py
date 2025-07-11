# Generated by Django 5.0.7 on 2025-03-17 13:46

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0006_absenceadmin'),
        ('anneeacademique', '0003_anneecademique_end_date_anneecademique_start_date'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='absenceadmin',
            name='anneeacademique',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='anneeacademique.anneecademique'),
        ),
        migrations.AlterField(
            model_name='absenceadmin',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='absencesadmin', to=settings.AUTH_USER_MODEL),
        ),
    ]
