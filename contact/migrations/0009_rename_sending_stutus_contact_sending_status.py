# Generated by Django 5.0.7 on 2025-04-04 04:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0008_alter_contact_sending_stutus'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contact',
            old_name='sending_stutus',
            new_name='sending_status',
        ),
    ]
