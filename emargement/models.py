from django.db import models
from django.contrib.auth.models import User
from anneeacademique.models import AnneeCademique
from salle.models import Salle
from matiere.models import Matiere


class Emargement(models.Model):
    MS = [
        ('Janvier', 'Janvier'),
        ('Février', 'Février'),
        ('Mars', 'Mars'),
        ('Avril', 'Avril'),
        ('Mai', 'Mai'),
        ('Juin', 'Juin'),
        ('Juillet', 'Juillet'),       
        ('Août', 'Août'),        
        ('Septembre', 'Septembre'),       
        ('Octobre', 'Octobre'),       
        ('Novembre', 'Novembre'),       
        ('Décembre', 'Décembre'),
    ]
    
    JR = [
        ('Lundi','Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
        ('Dimanche', 'Dimanche')
    ]
    
    SE = [
        ('Cours', 'Cours'),
        ('Travail Dirigé', 'Travail Dirigé'),
        ('Contrôle', 'Contrôle'),
        ('Travail Pratique', 'Travail Pratique')
    ]
    
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=True, blank=True)
    enseignant = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='emargement_enseignant')
    month = models.CharField(max_length=20, choices=MS, null=True)
    jour = models.CharField(max_length=10, choices=JR, null=True)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False,related_name='emargement_enregistrées_par')
       
    seance = models.CharField(max_length=300, choices=SE, null=True, blank=True)
    titre = models.CharField(max_length=100, null=True, blank=True)
    date_emargement = models.DateField(blank=True, auto_now_add=True)
    status = models.BooleanField(default=False, null=True)
