from django.db import models
#from django.contrib.auth.models import User
from app_auth.models import Student, Parent
from anneeacademique.models import AnneeCademique
from django.contrib.auth.models import User


class Contact(models.Model):
    TS = [
        ('Réclamation de notes', 'Réclamation de notes'),
        ('Harcèlement', 'Harcèlement'),
        ('Frais de scolarité', 'Frais de scolarité'),
        ('Autre', 'Autre')      
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, default=None)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, default=None)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, null=True, blank=True, default=None)
    subject = models.CharField(max_length=100, choices=TS, null=True)
    message = models.CharField(max_length=500, null=False)
    datecontact = models.DateTimeField(blank=True, auto_now_add=True)
    reading_status = models.IntegerField(default=0, null=True)
    delete_status = models.IntegerField(default=0, null=True)
    sending_status = models.BooleanField(default=True, null=True) # Statut pour indiquer l'expediteur (True pour l'admin et False pour l'étudiant ou le parent)
    
    def __str__(self):
        return self.message
    
class Message(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE)
    expediteur = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, related_name="expediteur")
    beneficiaire = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, related_name="beneficiaire")
    content = models.CharField(max_length=500, null=False)
    datemessage = models.DateTimeField(blank=True, auto_now_add=True)
    reading_status = models.IntegerField(default=0, null=True)
    delete_status = models.IntegerField(default=0, null=True)
    
    def __str__(self):
        return self.content
