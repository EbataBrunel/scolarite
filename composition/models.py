from django.db import models
from django.contrib.auth.models import User
from matiere.models import Matiere
from salle.models import Salle
from anneeacademique.models import AnneeCademique
from app_auth.models import Student

class Composer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=False)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True, related_name="compositions")
    evaluation = models.CharField(max_length=20, null=True)
    trimestre = models.CharField(max_length=20, null=True)
    note = models.DecimalField(max_digits=10, decimal_places=2, default=00.00, null=True)
    numerocontrole = models.CharField(max_length=20, null=True, default="")
    status = models.BooleanField(default=False, null=True) # Statut de lecture de l'étudiant
    status_parent = models.IntegerField(default=0, null=False) # Statut de lecture du parent
    
class Deliberation(models.Model):
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True, related_name="deliberations")
    trimestre = models.CharField(max_length=20, null=True)
    moyennevalidation = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, null=True)
    status = models.BooleanField(default=False)
    status_cloture = models.BooleanField(default=False, null=True)
    date_cloture = models.DateTimeField(blank=True, auto_now_add=True, null=True)