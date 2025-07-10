from django.db import models
from anneeacademique.models import AnneeCademique

class SettingSupUser(models.Model):
    appname = models.CharField(max_length=100)
    appeditor = models.CharField(max_length=200)
    phone = models.CharField(max_length=200, null=True)
    address = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=100)
    version = models.CharField(max_length=10, null=True)
    devise = models.CharField(max_length=10, null=True)
    COLORS = [
        ('bg-primary','bg-primary'),
        ('bg-info','bg-info'),
        ('bg-success','bg-success'),
        ('bg-danger','bg-danger'),
        ('bg-secondary','bg-secondary'),
        ('bg-dark','bg-dark')
    ]
    theme = models.CharField(max_length=200, null=True, choices=COLORS)
    CT = [
        ('text-primary','text-primary'),
        ('text-info','text-info'),
        ('text-success','text-success'),
        ('text-danger','text-danger'),
        ('text-secondary','text-secondary'),
        ('text-dark','text-dark'),
        ('text-light', 'text-light')
    ]
    text_color = models.CharField(max_length=20, null=True, choices=CT)
    logo = models.ImageField(upload_to="media", null=True, blank=True)
    width_logo = models.CharField(max_length=3, null=True)
    height_logo = models.CharField(max_length=3)

    def __str__(self):
        return self.appname

class Setting(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    appname = models.CharField(max_length=100)
    appeditor = models.CharField(max_length=200)
    phone = models.CharField(max_length=200, null=True)
    address = models.CharField(max_length=200, null=True)
    email = models.TextField(null=True)
    version = models.CharField(max_length=10, null=True)
    devise = models.CharField(max_length=10, null=True)
    COLORS = [
        ('bg-primary','bg-primary'),
        ('bg-info','bg-info'),
        ('bg-success','bg-success'),
        ('bg-danger','bg-danger'),
        ('bg-secondary','bg-secondary'),
        ('bg-dark','bg-dark')
    ]
    theme = models.CharField(max_length=200, null=True, choices=COLORS)
    CT = [
        ('text-primary','text-primary'),
        ('text-info','text-info'),
        ('text-success','text-success'),
        ('text-danger','text-danger'),
        ('text-secondary','text-secondary'),
        ('text-dark','text-dark'),
        ('text-light', 'text-light')
    ]
    text_color = models.CharField(max_length=20, null=True, choices=CT)
    logo = models.ImageField(upload_to="media", null=True, blank=True)
    width_logo = models.CharField(max_length=3, null=True)
    height_logo = models.TextField(max_length=3, null=True)

    def __str__(self):
        return self.appname
    
    

