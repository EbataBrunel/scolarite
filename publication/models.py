from django.db import models
from salle.models import Salle
from django.contrib.auth.models import User
from anneeacademique.models import AnneeCademique

class Publication(models.Model):
    title = models.CharField(max_length=100, null=False)
    file = models.FileField(upload_to="", null=False)
    comment = models.CharField(max_length=300, null=True)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    date_pub = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    
    def __str__(self):
        return self.title
    
