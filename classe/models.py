from django.db import models
from anneeacademique.models import AnneeCademique
from cycle.models import Cycle

class Classe(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, null=False, related_name="classes")
    libelle = models.CharField(max_length=100, null=False)
    
    def __str__(self):
        return self.libelle
