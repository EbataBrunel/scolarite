from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from anneeacademique.models import AnneeCademique
from salle.models import Salle
from app_auth.models import Student
from matiere.models import Matiere


class Cours(models.Model):
    anneeacademique = models.ForeignKey(AnneeCademique, on_delete=models.CASCADE, null=False)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, null=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, null=False)
    enseignant = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=False)
    title = models.CharField(max_length=100, null=True)
    comment = models.CharField(max_length=300, null=True)
    file=models.FileField(upload_to="upload", null=False)
    date = models.DateTimeField(blank=True, auto_now_add=True, null=True)
    
    
class CommentCours(models.Model):
    cours = models.ForeignKey(
        Cours, 
        on_delete=models.CASCADE, 
        null=False)
    author_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # Type de modèle de l'auteur
    author_object_id = models.PositiveIntegerField()  # ID de l'auteur
    author = GenericForeignKey('author_content_type', 'author_object_id')  # Auteur du commentaire (enseignant ou étudiant)
    content = models.TextField()  # Contenu du commentaire
    reading_status = models.IntegerField(null=False, default=0)
    date = models.DateTimeField(blank=True, auto_now_add=True, null=True)
    
    def is_teacher(self):
        """Vérifie si l'auteur est un enseignant."""
        return self.author_content_type.model == 'user'