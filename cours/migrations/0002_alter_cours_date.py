# Generated by Django 5.0.7 on 2024-12-12 19:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cours', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cours',
            name='date',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
