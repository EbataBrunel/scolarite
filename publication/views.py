# Importation des modules standards
import bleach
import os
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Count
from django.contrib import messages
# Importation des modules locaux
from .models import Publication
from salle.models import Salle
from inscription.models import Inscription
from anneeacademique.models import AnneeCademique
from renumeration.models import Contrat
from school.views import get_setting
from school.methods import get_file_hash
from app_auth.decorator import allowed_users, unauthenticated_customer
from scolarite.utils.crypto import chiffrer_param, dechiffrer_param

permission = ["Promoteur", "Directeur Général", "Directeur des Etudes", "Gestionnaire"]

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission)
def publications(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salle_publications=(Publication.objects.values("salle_id")
                          .filter(anneeacademique_id=anneeacademique_id)
                          .annotate(nb_publication=Count("salle_id")))
    tabPublications = []
    for s in salle_publications:
        salle = Salle.objects.get(id=s["salle_id"])
        dic = {}
        dic["salle"] = salle
        dic["nb_publication"] = s["nb_publication"]
        tabPublications.append(dic)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "publications": tabPublications,
        "anneeacademique": anneeacademique
    }
    return render(request, "publications.html", context=context)
        
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission)
def detail_publication(request, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    id = int(dechiffrer_param(str(salle_id)))
    salle = Salle.objects.get(id=id)
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    publications = Publication.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=id).select_related("user")
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "publications": publications,
        "salle": salle,
        "anneeacademique": anneeacademique
    }   
    return render(request, "detail_publication.html", context)
    
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission)
def add_publication(request):
    classe_id = request.session.get('classe_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":
        user_id = request.user.id
        
        title = bleach.clean(request.POST["title"].strip())
        file = request.FILES["file"]
        comment = bleach.clean(request.POST["comment"].strip())       
        salle_id = request.POST["salle"]
        
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)    
        
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
        if not file.name.endswith('.pdf'): # Vérifier l'extension du fichier
            return JsonResponse({"status":1})      
        elif file.size > 3 * 1024 * 1024: # Limiter la taille du fichier à 3 Mo
            return JsonResponse({
                "status": "error",
                "message": "La taille du fichier ne doit pas depassser 3 Mo."})
        else:
            
            publications = Publication.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id)
            liste_empreint_md5 = []
            for l in publications:
                liste_empreint_md5.append(get_file_hash(l.file))
                l.file.close()  # Fermer le fichier après le calcul du hash
                    
            if get_file_hash(file) in liste_empreint_md5:
                return JsonResponse({
                    "status": "success",
                    "message": "Cette publication existe déjà."})
            else:
                publication = Publication(
                    title=title,
                    file=file,
                    comment=comment,
                    salle_id=salle_id,
                    anneeacademique_id=anneeacademique_id,
                    user_id=user_id)
                
                count0 = Publication.objects.all().count()
                publication.save()
                count1 = Publication.objects.all().count()
                # Verifier si l'ajout a été bien effectué ou pas
                if count0 < count1:
                    return JsonResponse({
                        "status": "success",
                        "message": "Publication enregistrée avec succès."})
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "L'insertion a échouée."})
                
    salles = Salle.objects.filter(classe_id=classe_id)
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    context = {
        "setting": setting,
        "salles": salles,
        "contrat": contrat
    }
    return render(request, "add_publication.html", context)
                
                
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission)
def edit_publication(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    publication_id = int(dechiffrer_param(str(id)))
    publication = Publication.objects.get(id=publication_id)   
    classe_id = request.session.get('classe_id')
   
    salles = Salle.objects.filter(classe_id=classe_id).exclude(id=publication.salle.id)
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()             
    context = {
        "setting": setting,
        "publication": publication,
        "salles": salles,
        "contrat": contrat
    }
    return render(request, "edit_publication.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission)
def edit_pub(request):
   anneeacademique_id = request.session.get('anneeacademique_id') 
   if request.method == "POST":
        id = int(request.POST["id"])
        try:
            publication = Publication.objects.get(id=id)
        except:
            publication = None
        
        if publication:
            
            title = bleach.clean(request.POST["title"].strip())
            comment = bleach.clean(request.POST["comment"].strip())
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            file = None
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
            if request.POST.get('file', True):
                f = request.FILES["file"]
                # Vérifier l'extension du fichier
                if not f.name.endswith('.pdf'):
                    return JsonResponse({
                        "status": "error",
                        "message": "Le fichier doit être de format pdf."})      
                elif f.size > 3 * 1024 * 1024: # Limiter la taille du fichier à 3 Mo
                    return JsonResponse({
                        "status": "error",
                        "message": "La taille du fichier ne doit pas depasser 3Mo."})
                else:
                    file = f
                    
            salle_id = request.POST["salle"]

            if file is not None:
                publications = Publication.objects.all()
                liste_empreint_md5 = []
                for l in publications:
                    liste_empreint_md5.append(get_file_hash(l.file))
                    l.file.close()  # Fermer le fichier après le calcul du hash
                        
                if get_file_hash(file) in liste_empreint_md5:
                    return JsonResponse({
                        "status": "error",
                        "message": "Cette publication existe déjà."})
                else:
                    # Vérifier si la publication a un fichié associé et que le fichier existe réellement
                    if publication.file and hasattr(publication.file, 'path'):
                        #Suppression de la publication et en même temps du fichier
                        # Chemin complet du fichier
                        file_path = publication.file.path
                        # Verifier l'existence du fichier
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        
                publication.file = file
                
            publication.title = title
            publication.comment = comment
            publication.salle_id = salle_id

            publication.save()
            return JsonResponse({
                "status": "success",
                "message": "Publication modifiée avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission)       
def del_publication(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    contrat = Contrat.objects.filter(user=request.user, anneeacademique=anneeacademique).first()
    if contrat and contrat.status_signature:
        publication_id = int(dechiffrer_param(str(id)))
        publication = Publication.objects.get(id=publication_id)
        # Nombre de publications avant la suppression
        count0 = Publication.objects.all().count()
        pub_student.delete()
        # Nombre de publications après la suppression
        count1 = Publication.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
        return redirect("detail_publication", chiffrer_param(str(publication.salle.id)))
    else:
        messages.error(request, "Veuillez signer votre contrat avant de procéder à la suppression d’un programme.")
        return redirect("detail_publication", chiffrer_param(str(publication.salle.id)))
    


@unauthenticated_customer
def pub_student(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    student_id = request.session.get('student_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    insscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()
    
    publications = Publication.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=insscription.salle.id).order_by("-id")
    context = {
        "setting": setting,
        "publications": publications
    }   
    return render(request, "pub_student.html", context=context)





