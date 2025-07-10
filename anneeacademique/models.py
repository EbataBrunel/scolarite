from django.db import models
from etablissement.models import Etablissement

class AnneeCademique(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, null=True, default=None, related_name="anneeacademiques")
    annee_debut = models.IntegerField(default=2000, null=True)
    annee_fin =  models.IntegerField(default=2001, null=True)
    separateur = models.CharField(max_length=1, null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    status_cloture = models.BooleanField(default=True, null=False)
    status_access = models.BooleanField(default=True, null=False)
    
    def __str__(self):
        return f"{self.annee_debut}{self.separateur}{self.annee_fin}"
    
    

