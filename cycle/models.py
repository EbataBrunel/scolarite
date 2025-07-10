from django.db import models
from etablissement.models import Etablissement
from anneeacademique.models import AnneeCademique

class Cycle(models.Model):
    NAME = [
        ('Prescolaire','Prescolaire'),
        ('Primaire','Primaire'),
        ('Collège','Collège'),
        ('Lycée','Lycée')
    ]
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, null=False, related_name="cycles")
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    libelle = models.CharField(max_length=100, choices=NAME, null=True)
    
    def __str__(self):
        return self.libelle


