from django.db import models
from anneeacademique.models import AnneeCademique

class Trimestre(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, null=False)
    start_date = models.DateField()
    end_date = models.DateField()
    
    def __str__(self):
        return self.name
    
class EvenementScolaire(models.Model):
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, related_name="evenementscolaires")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name
