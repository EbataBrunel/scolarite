from django.db import models
from django.contrib.auth.models import User
from anneeacademique.models import AnneeCademique
from salle.models import Salle
from matiere.models import Matiere
from app_auth.models import Student
from emargement.models import Emargement


class Absence(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=True, blank=True)
    enseignant = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='absences_enseignant')
    jour = models.CharField(max_length=10)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='absences_enregistrées_par')
    date_absence = models.DateField(null=True, blank=True, auto_now_add=True)
    motif = models.CharField(max_length=300, null=True, blank=True, default="")
    status = models.BooleanField(default=False, null=True) # Marquer la lecture de l'enregistement l'absence
    status_decision = models.IntegerField(default=0, null=False) # Accepter ou refuser le motif de l'absence
    date_limite = models.DateTimeField(blank=True, null=False) # Date limite de justification de l'absence
    date_enregistrement = models.DateTimeField(null=False, auto_now_add=True) # Date d'enregistrement de l'absence
    
class Absencestudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=False)
    emargement = models.ForeignKey(Emargement, on_delete=models.CASCADE, null=False)
    motif = models.CharField(max_length=300, null=True, blank=True, default="")
    status = models.BooleanField(default=False, null=True) 
    status_parent = models.IntegerField(default=0, null=False)  # Marquer la lecture de l'enregistement l'absence
    status_decision = models.IntegerField(default=0, null=False) # Accepter ou refuser le motif de l'absence
    date_limite = models.DateTimeField(blank=True, null=False) # Date limite de justification de l'absence
    date_enregistrement = models.DateTimeField(null=False, auto_now_add=True) # Date d'enregistrement de l'absence
    
class AbsenceAdmin(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name="absencesadmin")
    admin = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name="administrateurs")
    date_absence = models.DateField(null=True, blank=True, auto_now_add=True)
    motif = models.CharField(max_length=300, null=True, blank=True, default="")
    status = models.BooleanField(default=False, null=True) # Marquer la lecture de l'enregistement l'absence
    status_decision = models.IntegerField(default=0, null=False) # Accepter ou refuser le motif de l'absence
    date_limite = models.DateTimeField(blank=True, null=False) # Date limite de justification de l'absence
    date_enregistrement = models.DateTimeField(null=False, auto_now_add=True) # Date d'enregistrement de l'absence
    
    
