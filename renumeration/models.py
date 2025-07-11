from django.db import models
from django.contrib.auth.models import User
from anneeacademique.models import AnneeCademique


class Renumeration(models.Model):
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
    
    MP = [
        ('Espèce', 'Espèce'), 
        ('Virement', 'Virement'), 
        ('Mobile', 'Mobile')
    ]
    
    TR = [
        ('Administrateur scolaire', 'Administrateur scolaire'),
        ('Enseignant du cycle fondamental', 'Enseignant du cycle fondamental'),
        ('Enseignant du cycle secondaire', 'Enseignant du cycle secondaire')
    ] 
    
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    month = models.CharField(max_length=20, choices=MS, null=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=False, 
        related_name='renumerations')
       
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    indemnite = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.CharField(max_length=1000, null=True)
    responsable = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=False,
        related_name='renumeration_enregistrées_par')
    date = models.DateField(blank=True, auto_now_add=True)
    status = models.BooleanField(default=False, null=True)
    mode_payment = models.CharField(max_length=20, choices=MP, null=False, default="Espèce")
    type_renumeration = models.CharField(max_length=40, choices=TR, default="Administrateur scolaire")

class Contrat(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    TC = [
        ('Administrateur scolaire', 'Administrateur scolaire'),
        ('Enseignant du cycle fondamental', 'Enseignant du cycle fondamental'),
        ('Enseignant du cycle secondaire', 'Enseignant du cycle secondaire')
    ]  
    type_contrat = models.CharField(max_length=40, choices=TC, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='contrats')    
    poste = models.CharField(max_length=100, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField()
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    date_contrat = models.DateTimeField(auto_now_add=True)
    admin = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        related_name='responsable_enregistre_contrat')
    status_signature = models.BooleanField(default=False, null=True) # Statut de la signature de l'utilisateur (False s'il n'a pas signé)
    date_signature = models.DateField(null=True, blank=True, auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"

  
    

    
