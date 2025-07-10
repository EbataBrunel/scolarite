from django.db import models
from django.contrib.auth.models import User
from salle.models import Salle
from matiere.models import Matiere
from anneeacademique.models import AnneeCademique 
from app_auth.models import Student

class Enseigner(models.Model):
    TRIM = [
        ('Trimestre 1','Trimestre 1'),
        ('Trimestre 2','Trimestre 2'),
        ('Trimestre 3','Trimestre 3')
    ]
    enseignant = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=False)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    volumehoraire = models.IntegerField(default=1)
    cout_heure = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, null=True)
    trimestre = models.CharField(max_length=20, choices=TRIM, null=True)
    eval = models.BooleanField(default=False, null=True)
    date_eval = models.DateTimeField(blank=True, auto_now_add=True, null=True)
    
    
class EvaluationEnseignant(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=False)
    enseignant = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=False)
    justification = models.CharField(max_length=20, null=True)
    note = models.DecimalField(max_digits=10, decimal_places=2, default=00.00, null=True)
    dateeval = models.DateTimeField(null=True, auto_now_add=True)