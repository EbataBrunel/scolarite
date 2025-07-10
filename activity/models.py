from django.db import models
from django.contrib.auth.models import User
from anneeacademique.models import AnneeCademique

class Activity(models.Model):
    TP = [
        ('Publique','Publique'),
        ('Privée', 'Privée')       
    ]
    type = models.CharField(max_length=20, choices=TP, null=True)
    content = models.CharField(max_length=300, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    date = models.DateTimeField(null=True, blank=True, auto_now_add=True)
