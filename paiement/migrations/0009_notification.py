# Generated by Django 5.0.7 on 2025-04-13 16:43

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anneeacademique', '0003_anneecademique_end_date_anneecademique_start_date'),
        ('app_auth', '0002_alter_student_photo'),
        ('paiement', '0008_payment_mode_paiement'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.CharField(choices=[('Janvier', 'Janvier'), ('Février', 'Février'), ('Mars', 'Mars'), ('Avril', 'Avril'), ('Mai', 'Mai'), ('Juin', 'Juin'), ('Juillet', 'Juillet'), ('Août', 'Août'), ('Septembre', 'Septembre'), ('Octobre', 'Octobre'), ('Novembre', 'Novembre'), ('Décembre', 'Décembre')], max_length=20, null=True)),
                ('amount', models.DecimalField(decimal_places=2, default=10.0, max_digits=10, null=True)),
                ('date_notification', models.DateTimeField(auto_now_add=True, null=True)),
                ('anneeacademique', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='anneeacademique.anneecademique')),
                ('parent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app_auth.parent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
