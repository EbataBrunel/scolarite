from django.db import models
from matiere.models import Matiere
from salle.models import Salle
from anneeacademique.models import AnneeCademique

class Programme(models.Model):
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=False)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    coefficient = models.IntegerField(default=1)
