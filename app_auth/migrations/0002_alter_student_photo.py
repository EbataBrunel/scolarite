# Generated by Django 5.0.7 on 2024-11-09 19:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_auth', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='img'),
        ),
    ]
