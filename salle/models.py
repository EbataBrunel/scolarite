from django.db import models
from serie.models import Serie
from classe.models import Classe
from anneeacademique.models import AnneeCademique
from cycle.models import Cycle

class Salle(models.Model): 
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, null=False, related_name="salles")
    serie = models.ForeignKey(Serie, on_delete=models.CASCADE, null=True, default=None)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    number = models.CharField(max_length=20, default="")
    max_student = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    price_inscription = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, null=False)
    
    def __str__(self):
        if self.serie:
            return f"{self.classe.libelle} {self.serie.name}{self.number}"
        else:
            if self.number:
                return f"{self.classe.libelle}-{self.number}"
            else:
                return f"{self.classe.libelle}"
    