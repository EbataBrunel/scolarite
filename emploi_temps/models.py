from django.db import models
from django.contrib.auth.models import User
from salle.models import Salle
from matiere.models import Matiere
from anneeacademique.models import AnneeCademique 

class EmploiTemps(models.Model):
    JOUR_CHOICES = [
        ('LUNDI', 'Lundi'),
        ('MARDI', 'Mardi'),
        ('MERCREDI', 'Mercredi'),
        ('JEUDI', 'Jeudi'),
        ('VENDREDI', 'Vendredi'),
        ('SAMEDI', 'Samedi'),
        ('DIMANCHE', 'Dimanche'),
    ]
    
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=False)
    enseignant = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    jour = models.CharField(max_length=10, choices=JOUR_CHOICES)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    
    def __str__(self):
        return str(self.heure_debut)+" - "+str(self.heure_fin)