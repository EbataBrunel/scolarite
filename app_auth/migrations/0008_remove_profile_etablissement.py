# Generated by Django 5.0.7 on 2025-05-27 01:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_auth', '0007_parent_status_access'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='etablissement',
        ),
    ]
