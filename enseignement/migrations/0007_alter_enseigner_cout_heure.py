# Generated by Django 5.0.7 on 2025-07-10 22:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enseignement', '0006_rename_date_eval_1_enseigner_date_eval_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enseigner',
            name='cout_heure',
            field=models.DecimalField(blank=True, decimal_places=2, default=10.0, max_digits=10, null=True),
        ),
    ]
