# Generated by Django 5.0.7 on 2025-05-09 19:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_auth', '0004_profile_etablissement'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='address',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
