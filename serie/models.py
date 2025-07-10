from django.db import models
from anneeacademique.models import AnneeCademique

class Serie(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    name = models.CharField(max_length=20)
    
    def __str__(self):
        return self.name
    
    
