from django.db import models
from anneeacademique.models import AnneeCademique
from cycle.models import Cycle

class Matiere(models.Model):
    BG = [
        ('bg-primary','bg-primary'),
        ('bg-info','bg-info'),
        ('bg-success','bg-success'),
        ('bg-danger','bg-danger'),
        ('bg-secondary','bg-secondary'),
        ('bg-dark','bg-dark')
    ]
    
    CT = [
        ('text-primary','text-primary'),
        ('text-info','text-info'),
        ('text-success','text-success'),
        ('text-danger','text-danger'),
        ('text-secondary','text-secondary'),
        ('text-dark','text-dark'),
        ('text-light', 'text-light')
    ]
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, null=False, related_name="matieres")
    libelle = models.CharField(max_length=100, null=True)
    abreviation = models.CharField(max_length=50, null=True)
    theme = models.CharField(max_length=20, choices=BG, null=True)
    text_color = models.CharField(max_length=20, choices=CT, null=True)
    
    def __str__(self):
        return self.libelle


