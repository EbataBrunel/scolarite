# Generated by Django 5.0.7 on 2025-04-20 14:26

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0013_remove_contact_status_admin_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='beneficiaire',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='beneficiaire', to=settings.AUTH_USER_MODEL),
        ),
    ]
