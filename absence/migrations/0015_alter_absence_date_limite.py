# Generated by Django 5.0.7 on 2025-06-30 21:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0014_absence_date_limite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='absence',
            name='date_limite',
            field=models.DateTimeField(blank=True),
        ),
    ]
