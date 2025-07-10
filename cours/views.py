# Importation des modules standards
import bleach
import hashlib
import os
# Importation des modules tiers
from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
# Importation des modules locaux
from .models import Cours, CommentCours
from enseignement.models import Enseigner
from salle.models import Salle
from matiere.models import Matiere
from inscription.models import Inscription
from app_auth.models import Student
from school.views import get_setting
from scolarite.utils.crypto import dechiffrer_param

def get_file_hash(file):
    hash_md5 = hashlib.md5() # Cette objet de MD5 servira de stocker et calculer l'empreinte MD5.
    for chunk in file.chunks(): # Parcourir le fichier par morceau pour ne pas surcherger la memoire
        hash_md5.update(chunk) # Ajout de chaque morceau au calcul de hash et en mettant en même à jour le hash
    return hash_md5.hexdigest() # retourner l'empreinte MD5 sous forme de chaîne hexadécimale

def cours(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_cours = (Cours.objects.values("salle_id")
             .filter(enseignant_id=user_id, anneeacademique_id=anneeacademique_id)
             .annotate(nb_matiere=Count("salle_id")))
    
    tabCours = []
    for sc in salles_cours:
        dic = {}
        salle_id = sc["salle_id"]
        salle = Salle.objects.get(id=salle_id)
        
        dic["salle"] = salle
        matieres_cours = (Cours.objects.values("matiere_id")
                          .filter(enseignant_id=user_id, salle_id=salle_id, anneeacademique_id=anneeacademique_id)
                          .annotate(nb_cours=Count("matiere_id")))
        
        matieres = []
        for mc in matieres_cours:
            dic_matiere = {}
            matiere_id = mc["matiere_id"]
            matiere = Matiere.objects.get(id=matiere_id)
            
            dic_matiere["matiere"] = matiere
            dic_matiere["nb_cours"] = mc["nb_cours"]
            
            list_cours = Cours.objects.filter(salle_id=salle_id, matiere_id=matiere_id, anneeacademique_id=anneeacademique_id)
            if list_cours.count() > 0:
                nb_newcomment = 0
                for cours in list_cours:
                    comments = CommentCours.objects.filter(cours=cours, reading_status=0)
                    
                    for comment in comments:
                        # Verifier si le commentaire appartient à l'étudiant
                        # Récupérer le commentaire
                        commentaire = get_object_or_404(CommentCours, id=comment.id)

                        # Vérifier si l'auteur est un étudiant
                        student_type = ContentType.objects.get_for_model(User)  # Type de modèle pour Student
                        if commentaire.author_content_type != student_type:
                           nb_newcomment += 1
                                    
                dic_matiere["nb_newcomment"] = nb_newcomment
            
            matieres.append(dic_matiere)
            
        dic["matieres"] = matieres
        
        tabCours.append(dic)
    
    context = {
        "setting": setting,
        "cours": tabCours
    }
    return render(request, "cours.html", context)


def detail_cours(request, salle_id, matiere_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    sl_id = int(dechiffrer_param(str(salle_id)))
    mt_id = int(dechiffrer_param(str(matiere_id)))
    
    salle = Salle.objects.get(id=sl_id)
    matiere = Matiere.objects.get(id=mt_id)
    list_cours = Cours.objects.filter(salle_id=sl_id, matiere_id=mt_id, enseignant_id=user_id, anneeacademique_id=anneeacademique_id)
    """
    if cours.count() > 0:
            dic = {}
            dic["matiere"] = matiere
            nb_newcomment = 0
            for cours in list_cours:
                comments = CommentCours.objects.filter(cours=cours)
                
                for comment in comments:
                    # Verifier si le commentaire appartient à l'étudiat
                    # Récupérer le commentaire
                    commentaire = get_object_or_404(CommentCours, id=comment.id)

                    # Vérifier si l'auteur est un étudiant
                    student_type = ContentType.objects.get_for_model(Student)  # Type de modèle pour Student
                    if commentaire.author_content_type != student_type:
                        dic_comment = eval(comment.reading_status)
                        if dic_comment:
                            for key in dic_comment.values():
                                if key != request.user.id:
                                    nb_newcomment += 1
                        else:
                            nb_newcomment += 1
                                
            dic["nb_newcomment"] = nb_newcomment
        
            matieres.append(dic)"""
            
    context = {
        "setting": setting,
        "cours": list_cours,
        "salle": salle,
        "matiere": matiere
    }
    
    return render(request, "detail_cours.html", context)


@login_required(login_url='connection/login')
def add_cours(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        title = bleach.clean(request.POST["title"].strip())
        file = request.FILES["file"]
        comment = bleach.clean(request.POST["comment"].strip())
        
        salle_id = request.POST["salle"]
        matiere_id = request.POST["matiere"]
        
        # Vérifier l'extension du fichier
        if not file.name.endswith('.pdf'):
            return JsonResponse({
                    "status": "error",
                    "message": "Le fichier doit être au format PDF."})     
        elif file.size > 3 * 1024 * 1024: # Limiter la taille du fichier à 3 Mo
            return JsonResponse({
                    "status": "error",
                    "message": "La taille du fichier est limitée à 3Mo."})
        else:
            
            liste_cours = Cours.objects.all()
            liste_empreint_md5 = []
            for l in liste_cours:
                liste_empreint_md5.append(get_file_hash(l.file))
                l.file.close()  # Fermer le fichier après le calcul du hash
                    
            if get_file_hash(file) in liste_empreint_md5:
                return JsonResponse({
                    "status": "error",
                    "message": "Ce cours existe déjà."})
            else:
                cours = Cours(
                    anneeacademique_id=anneeacademique_id,
                    salle_id=salle_id,
                    matiere_id=matiere_id,
                    enseignant_id=user_id,
                    title=title,
                    comment=comment,
                    file=file)
                count0 = Cours.objects.all().count()
                cours.save()
                count1 = Cours.objects.all().count()
                # Verifier si l'ajout a été bien effectué ou pas
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Cours mis en ligne avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})
        
    salles_enseignements = (Enseigner.objects.values("salle_id")
                    .filter(anneeacademique_id=anneeacademique_id, enseignant_id=user_id)
                    .annotate(nb_salles=Count("salle_id")))
    
    salles = []
    for se in salles_enseignements:
        salle = Salle.objects.get(id=se["salle_id"])
        salles.append(salle)
        
    context = {       
        "salles": salles,
        "setting": setting
    }
    return render(request, "add_cours.html", context)

@login_required(login_url='connection/login')
def edit_cours(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id 
    
    cours_id = int(dechiffrer_param(str(id)))
    
    cours = Cours.objects.get(id=cours_id)   
    #Vérifier si ce membre est authorisé à acceder à cette page ou pas.
    query = Cours.objects.filter(id=cours_id, enseignant_id=request.user.id)
    if query.exists():
    
        salles_enseignements = (Enseigner.objects.values("salle_id")
                         .filter(enseignant_id=user_id, anneeacademique_id=anneeacademique_id)
                         .annotate(nb_ens_salle=Count("salle_id")))
        
        tabSalles = []
        for se in salles_enseignements:
            salle = Salle.objects.get(id=se["salle_id"])
            if salle.id != cours.salle.id:
                tabSalles.append(salle)

        matieres_enseignements = (Enseigner.objects.values("matiere_id")
                         .filter(enseignant_id=user_id, anneeacademique_id=anneeacademique_id)
                         .annotate(nb_ens_mat=Count("matiere_id")))
        tabMatiere = []
        for me in matieres_enseignements:
            matiere = Matiere.objects.get(id=me["matiere_id"])
            if matiere.id != cours.matiere.id:
                tabMatiere.append(matiere)
                
        context = {
            "setting": setting,
            "cours": cours,
            "salles": tabSalles,
            "matieres": tabMatiere,
        }
        return render(request, "edit_cours.html", context)
    else:
        return redirect("settings/authorization")

@login_required(login_url='connection/login')
def edit_cour(request):
   
   if request.method == "POST":
        id = request.POST["id"]
        try:
            cours = Cours.objects.get(id=id)
        except:
            cours = None
        
        if cours:
            title = bleach.clean(request.POST["title"].strip())                    
            comment = bleach.clean(request.POST["comment"].strip())
            salle_id = request.POST["salle"]
            matiere_id = request.POST["matiere"]

            file = None
            if request.POST.get('file', True):
                f = request.FILES["file"]
                # Vérifier l'extension du fichier
                if not f.name.endswith('.pdf'):
                    return JsonResponse({
                        "status": "error",
                        "message": "Le fichier doit être au format PDF."}) 
                elif f.size > 10 * 1024 * 1024: # Limiter la taille du fichier à 10 Mo
                    return JsonResponse({
                        "status": "error",
                        "message": "La taille du fichier est limitée à 10Mo."})
                else:
                    file = f

            cours.title = title
            if file is not None:
                liste_cours = Cours.objects.all()
                liste_empreint_md5 = []
                for l in liste_cours:
                    liste_empreint_md5.append(get_file_hash(l.file))
                    l.file.close()  # Fermer le fichier après le calcul du hash
                        
                if get_file_hash(file) in liste_empreint_md5:
                    return JsonResponse({
                        "status": "error",
                        "message": "Ce fichier existe déjà."})
                else:
                    # Vérifier si la lettre de motivation a un fichié associé et que le fichier existe réellement
                    if cours.file and hasattr(cours.file, 'path'):
                        #Suppression de la lettre de motivation et en même temps du fichier
                        # Chemin complet du fichier
                        file_path = cours.file.path
                        # Verifier l'existence du fichier
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        
                cours.file = file
            cours.comment = comment
            cours.salle_id = salle_id
            cours.matiere_id = matiere_id

            cours.save()
            return JsonResponse({
                    "status": "success",
                    "message": "Fichier mis en ligne avec succès."})
        
        
# Récuperer les matières enseignées dans une salle     
class mat_enseignant(View):
    def get(self, request, salle_id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        matieres_enseignements = (Enseigner.objects.values("matiere_id")
                         .filter(enseignant_id=request.user.id, salle_id=salle_id, anneeacademique_id=anneeacademique_id)
                         .annotate(nb_matiere=Count("matiere_id")))
        matieres = []
        for me in matieres_enseignements:
            matiere = Matiere.objects.get(id=me["matiere_id"])
            matieres.append(matiere)

        context = {
            "matieres": matieres
        }
        return render(request, "mat_enseignant.html", context)
    
def del_cours(request, id):
    try:
        cours_id = int(dechiffrer_param(str(id)))
        cours = Cours.objects.get(id=cours_id)
    except:
        cours = None
        
    if cours:
        cours.delete()
    
    redirect("detail_coursligne", cours.salle.id, cours.matiere.id)
    
def cours_ligne(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    student_id = request.session.get('student_id')
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()
    
    matieres_enseignements = (Enseigner.objects.values("matiere_id")
                    .filter(salle_id=inscription.salle.id, anneeacademique_id=anneeacademique_id)
                    .annotate(nb_mat=Count("matiere_id")))
    
    matieres = []
    for me in matieres_enseignements:
        matiere = Matiere.objects.get(id=me["matiere_id"])
        list_cours = Cours.objects.filter(salle_id=inscription.salle.id, matiere_id=me["matiere_id"], anneeacademique_id=anneeacademique_id)
        if list_cours.count() > 0:
            dic = {}
            dic["matiere"] = matiere
            nb_newcomment = 0
            for cours in list_cours:
                comments = CommentCours.objects.filter(cours=cours, reading_status=0)
                for comment in comments:
                    # Récupérer le commentaire
                    commentaire = get_object_or_404(CommentCours, id=comment.id)
                    # Vérifier si l'auteur est un étudiant
                    student_type = ContentType.objects.get_for_model(Student)  # Type de modèle pour Student
                    if commentaire.author_content_type != student_type:
                        nb_newcomment += 1
                                
            dic["nb_newcomment"] = nb_newcomment
        
            matieres.append(dic)
        
    context = {
        "setting": setting,
        "matieres": matieres,
        "salle": inscription.salle
    }
    
    return render(request, "cours_ligne.html", context)

def detail_coursligne(request, salle_id, matiere_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    sl_id = int(dechiffrer_param(str(salle_id)))
    mt_id = int(dechiffrer_param(str(matiere_id)))
    
    matiere = Matiere.objects.get(id=mt_id)
    cours = Cours.objects.filter(
        salle_id=sl_id, 
        matiere_id=mt_id, 
        anneeacademique_id=anneeacademique_id).order_by("-id")
    
    # Changement de status des commentaires pour marquer qu'ils sont déjà lus
    for cour in cours:
        if request.user:
            comments = CommentCours.objects.filter(cours=cour, reading_status=0).exclude(author_object_id=request.user.id)
            for comment in comments:
                comment.reading_status = 1
                comment.save()
        else:
            comments = CommentCours.objects.filter(cours=cour, reading_status=0).exclude(author_object_id=request.session.get('student_id'))
            for comment in comments:
                comment.reading_status = 1
                comment.save()
    
    tabCours = []
    for c in cours:
        dic = {}
        dic["cours"] = c
        # Récuperer les commentaires de cd cours
        comments = CommentCours.objects.filter(cours=c).order_by("-id")
        dic["comments"] = comments 
        dic["nb_comments"] = comments.count()    
        nb_newcomment = 0
        # Récupérer le commentaire
        for comment in comments:
            commentaire = get_object_or_404(CommentCours, id=comment.id)

            # Vérifier si l'auteur est un étudiant
            student_type = ContentType.objects.get_for_model(User)  # Type de modèle pour Student
            if commentaire.author_content_type != student_type:
                nb_newcomment += 1
                    
        dic["nb_newcomment"] = nb_newcomment                        
        tabCours.append(dic)
    
    salle = Salle.objects.get(id=sl_id)      
    
    if request.user.is_authenticated:
        template_name = 'global/base.html'
    else:
        template_name = 'global/base_customer.html'

    context = {
        "setting": setting,
        "cours": tabCours,
        "salle": salle,
        "matiere": matiere,
        "template_name": template_name
    }
    
    return render(request, "detail_coursligne.html", context) 

def add_commentcours(request):
    
    if request.method == "POST":
        content = bleach.clean(request.POST["content"].strip())
        cours_id = request.POST["cours_id"]
        cours = Cours.objects.get(id=cours_id)  # Exemple de cours
        if request.user.id:
            enseignant = User.objects.get(id=request.user.id)  # Exemple d'enseignant
            CommentCours.objects.create(
                cours=cours,
                author_content_type=ContentType.objects.get_for_model(User),
                author_object_id=enseignant.id,
                content=content
            ) 
            comments = CommentCours.objects.filter(cours=cours).order_by("-id")
            context = {
                "cours_id": cours_id,
                "comments": comments,
                "nb_comments": comments.count()
            }            
            return render(request, "content_commentcours.html", context)
        
        if request.session.get('student_id'):
            student_id = request.session.get('student_id')
            student = Student.objects.get(id=student_id)  # Exemple d'étudiant

            CommentCours.objects.create(
                cours=cours,
                author_content_type=ContentType.objects.get_for_model(Student),
                author_object_id=student.id,
                content=content
            )
            
            comments = CommentCours.objects.filter(cours=cours).order_by("-id")
            context = {
                "comments": comments,
                "nb_comments": comments.count()
            }            
            return render(request, "content_commentcours.html", context)
        
class delete_comment(View):
    def get(self, request, salle_id, id, *args, **kwargs):
        comment = CommentCours.objects.get(id=id)       
        cours = comment.cours    
        nb_comment = CommentCours.objects.filter(cours=cours).count()  
        comment.delete() 
        total_comment = nb_comment - 1      
        return JsonResponse({'status': 1, 'nb_comment': total_comment})
        
