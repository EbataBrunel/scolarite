# Generated by Django 5.0.7 on 2024-12-15 16:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('renumeration', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='renumeration',
            name='total_amount',
            field=models.CharField(max_length=1000, null=True),
        ),
    ]
