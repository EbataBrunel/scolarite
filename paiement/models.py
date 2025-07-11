from django.db import models
from django.contrib.auth.models import User
from anneeacademique.models import AnneeCademique
from app_auth.models import Student, Parent
from salle.models import Salle
from etablissement.models import Etablissement


class AutorisationPayment(models.Model):
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
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True)
    month = models.CharField(max_length=20, choices=MS, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    justification = models.TextField()
    date_autorisation = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    
class AutorisationPaymentSalle(models.Model):
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
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=True)
    month = models.CharField(max_length=20, choices=MS, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    justification = models.TextField()
    date_autorisation = models.DateTimeField(null=True, blank=True, auto_now_add=True)


class Payment(models.Model):
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
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True)
    month = models.CharField(max_length=20, choices=MS, null=True)
    mode_paiement = models.CharField(max_length=50, choices=MP, null=True, default="Espèce")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, null=True)
    datepaye = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    status = models.BooleanField(default=False, null=True)
    status_parent = models.BooleanField(default=False, null=True)
    
    
class Notification(models.Model):
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
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=True)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, null=True)
    month = models.CharField(max_length=20, choices=MS, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, null=True)
    date_notification = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    status = models.BooleanField(default=False, null=True) # Statut de lecture
    

class ContratEtablissement(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, null=False, related_name="contrat_etablissements")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField()
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    date_contrat = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=False, 
        related_name='resp_enregistre_contrat')
    status_signature = models.BooleanField(default=False, null=True) # Statut de la signature de l'utilisateur (False s'il n'a pas signé)
    date_signature = models.DateField(null=True, blank=True, auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"

class AutorisationPaymentEtablissement(models.Model):
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
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, null=False)
    month = models.CharField(max_length=20, choices=MS, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    justification = models.TextField()
    date_autorisation = models.DateTimeField(null=True, blank=True, auto_now_add=True)   
    
class PaymentEtablissement(models.Model):
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
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, null=False, related_name="payment_etablissements")
    month = models.CharField(max_length=20, choices=MS, null=False)
    number_student = models.IntegerField(default=1, null=False)
    amount_student = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, null=False)
    date_payment = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    mode_payment = models.CharField(max_length=20, null=False)
    status = models.BooleanField(default=False, null=False) # Statut de lecture
    transaction_id = models.CharField(max_length=100, null=True, default="")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    