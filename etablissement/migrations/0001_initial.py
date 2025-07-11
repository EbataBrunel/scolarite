# Generated by Django 5.0.7 on 2025-05-07 13:34

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Etablissement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=200)),
                ('email', models.CharField(max_length=100)),
                ('ville', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=200)),
                ('status_access', models.BooleanField(default=True)),
                ('promoteur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='etablissements', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='superuser', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
