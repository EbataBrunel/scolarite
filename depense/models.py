from django.db import models
from django.contrib.auth.models import User
from anneeacademique.models import AnneeCademique
from simple_history.models import HistoricalRecords

class Depense(models.Model):
    SIG = [
        ('Entrée', 'Entrée'),
        ('Sortie', 'Sortie')       
    ]
    
    TD = [
        ("Frais du loyer", "Frais du loyer"),
        ("Frais de l'électricité", "Frais de l'électricité"),
        ("Frais de l'internet", "Frais de l'internet"), 
        ("Frais du téléphone", "Frais du téléphone"),
        ("Travaux", "Travaux"),
        ("Don", "Don"),
        ("Autre", "Autre")       
    ]
    
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
    month = models.CharField(max_length=20, choices=MS, null=True)
    signe = models.CharField(max_length=20, choices=SIG, null=True)
    type_depense = models.CharField(max_length=200, choices=TD, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_depense = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    history = HistoricalRecords()