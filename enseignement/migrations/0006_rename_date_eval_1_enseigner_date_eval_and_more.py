# Generated by Django 5.0.7 on 2024-12-20 21:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('enseignement', '0005_evaluationenseignant_anneeacademique'),
    ]

    operations = [
        migrations.RenameField(
            model_name='enseigner',
            old_name='date_eval_1',
            new_name='date_eval',
        ),
        migrations.RenameField(
            model_name='enseigner',
            old_name='eval_1',
            new_name='eval',
        ),
        migrations.RemoveField(
            model_name='enseigner',
            name='date_eval_2',
        ),
        migrations.RemoveField(
            model_name='enseigner',
            name='date_eval_3',
        ),
        migrations.RemoveField(
            model_name='enseigner',
            name='eval_2',
        ),
        migrations.RemoveField(
            model_name='enseigner',
            name='eval_3',
        ),
    ]
