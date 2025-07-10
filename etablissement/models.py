from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

class Etablissement(models.Model):
    promoteur = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name="etablissements")
    name = models.CharField(max_length=200, null=False)
    abreviation = models.CharField(max_length=100, null=False)
    phone = models.CharField(max_length=200, null=False)
    email = models.CharField(max_length=100, null=False)
    ville = models.CharField(max_length=100, null=False)
    address = models.CharField(max_length=200, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name="superuser")
    date = models.DateTimeField(blank=True, auto_now_add=True)
    status_access = models.BooleanField(default=True, null=False)
    
    groups = models.ManyToManyField(Group)

    def __str__(self):
        return self.name