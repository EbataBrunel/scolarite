# Generated by Django 5.0.7 on 2025-05-07 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0004_setting_address_alter_setting_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='SettingSupUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('appname', models.CharField(max_length=100)),
                ('appeditor', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=200, null=True)),
                ('address', models.CharField(max_length=200, null=True)),
                ('email', models.TextField(null=True)),
                ('version', models.CharField(max_length=10, null=True)),
                ('devise', models.CharField(max_length=10, null=True)),
                ('theme', models.CharField(choices=[('bg-primary', 'bg-primary'), ('bg-info', 'bg-info'), ('bg-success', 'bg-success'), ('bg-danger', 'bg-danger'), ('bg-secondary', 'bg-secondary'), ('bg-dark', 'bg-dark')], max_length=200, null=True)),
                ('text_color', models.CharField(choices=[('text-primary', 'text-primary'), ('text-info', 'text-info'), ('text-success', 'text-success'), ('text-danger', 'text-danger'), ('text-secondary', 'text-secondary'), ('text-dark', 'text-dark'), ('text-light', 'text-light')], max_length=20, null=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='media')),
                ('width_logo', models.CharField(max_length=3, null=True)),
                ('height_logo', models.TextField(max_length=3, null=True)),
            ],
        ),
    ]
