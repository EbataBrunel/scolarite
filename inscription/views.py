
# Importation des modules standards
import pdfkit
import bleach
import re
import base64
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum
from decimal import Decimal
from django.contrib import messages
from django.http.response import HttpResponse
from django.template.loader import get_template
from django.contrib.sites.shortcuts import get_current_site
# Importation des modules locaux
from .models import*
from enseignement.models import Enseigner
from app_auth.models import Parent, EtablissementUser
from school.views import get_setting
from app_auth.decorator import allowed_users
from scolarite.utils.crypto import dechiffrer_param
from datetime import date

permission_user = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire', 'Surveillant Général']
permission_admin = ['Promoteur', 'Directeur Général', 'Directeur des Etudes', 'Gestionnaire']
permission_gestionnaire = ['Promoteur', 'Directeur Général', 'Gestionnaire']
permission_DG = ['Promoteur', 'Directeur Général']
permission_enseignant = ['Enseignant']


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def inscriptions(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    classe_id = request.session.get('classe_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
        
    salles_groupes = (Inscription.objects.values("salle_id")
                      .filter(anneeacademique_id=anneeacademique_id)
                      .annotate(effectif=Count("salle_id"))
    )
    tabInscription = []
    total = 0
    student_total = 0
    for salle in salles_groupes:
        s = Salle.objects.get(id=salle["salle_id"])
        if s.classe.id == classe_id:
            dic = {}
            dic["salle"] = s
            effectif = salle["effectif"] 
            dic["effectif"] = effectif
            # Calculer la somme des inscriptions d'une salle
            somme_inscription = (Inscription.objects.filter(salle_id=s.id, anneeacademique_id=anneeacademique_id).aggregate(Sum("amount"))["amount__sum"] or 0)
            dic["somme_inscription"] = somme_inscription
            tabInscription.append(dic)
            
            student_total += effectif
            total += somme_inscription
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)        
    context = {
        "setting": setting,
        "inscriptions": tabInscription,
        "total": total,
        "student_total": student_total,
        "anneeacademique": anneeacademique
    }
    return render(request, "inscriptions.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_admin)
def detail_inscription(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salle_id = int(dechiffrer_param(str(id)))
    salle = Salle.objects.get(id=salle_id)
    inscriptions = Inscription.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id)
    # Calculer la somme des inscriptions
    somme_inscription = (Inscription.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id).aggregate(Sum("amount"))["amount__sum"] or 0)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    context = {
        "setting": setting,
        "inscriptions": inscriptions,
        "salle": salle,
        "somme_inscription": somme_inscription,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_inscription.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_inscription(request):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    cycle_id = request.session.get('cycle_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    if request.method == "POST":   
             
        student_id = request.POST["student"]
        amount = bleach.clean(request.POST["amount"].strip())
        salle_id = request.POST["salle"]
        photo = None
        if request.POST.get('photo', True):
            photo = request.FILES["photo"]
            
        user_id = request.user.id        
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = amount.replace(" ", "").replace(",", ".")

        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
        
        query = Inscription.objects.filter(student_id=student_id, etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id)    
        # Récuperer la salle 
        salle  = Salle.objects.get(id=salle_id)
        # Nombre d'inscriptions avant l'ajout
        count0 = Inscription.objects.all().count()
        nb_student = count0 + 1 # Nombre d'étudiant après l'ajout
        
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
        if  nb_student > salle.max_student: # Verifier le quota
            return JsonResponse({
                "status": "error",
                "message": "Le nombre total d'élèves exigés dans cette salle depassé."})
        # Verifier si le montant corresponds à celui de la salle
        if salle.price_inscription != amount:
             return JsonResponse({
                "status": "error",
                "message": "Le montant renseigné ne correspond pas au frais d'inscription de cette salle."})   
        
        if query.exists():
            return JsonResponse({
                "status": "error",
                "message": "Cette inscription existe déjà."})
        else:
            inscription = Inscription(
                etablissement_id=etablissement_id,
                salle_id=salle_id, 
                student_id=student_id, 
                amount=amount, 
                anneeacademique_id=anneeacademique_id, 
                user_id=user_id,
                photo=photo)
            
            inscription.save()
            # Nombre d'inscriptions après l'ajout
            count1 = Inscription.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Inscription enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Inscription a échouée."}) 
    
    classe_id = request.session.get('classe_id')       
    salles = Salle.objects.filter(classe_id=classe_id, cycle_id=cycle_id, anneeacademique_id=anneeacademique_id)
    students = Student.objects.filter(etablissement_id=etablissement_id)
    mode_paiements = ["Espèce", "Virement", "Mobile"]
    context = {
        "setting": setting,
        "salles": salles,
        "students":students,
        "mode_paiements": mode_paiements
    }
    return render(request, "add_inscription.html", context) 

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_inscription(request,id):
    cycle_id = request.session.get('cycle_id')  
    classe_id = request.session.get('classe_id')  
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    inscription_id = int(dechiffrer_param(str(id)))
    inscription = Inscription.objects.get(id=inscription_id)
    students = Student.objects.filter(etablissement_id=etablissement_id).exclude(id=inscription.student.id)
    salles = Salle.objects.filter(classe_id=classe_id, cycle_id=cycle_id, anneeacademique_id=anneeacademique_id).exclude(id=inscription.salle.id)
    mode_paiements = ["Espèce", "Virement", "Mobile"]
    tab_mode_paiements = [mode_paiement for mode_paiement in mode_paiements if mode_paiement != inscription.mode_paiement]
    
    context = {            
            "inscription": inscription,
            "salles": salles,
            "students": students,
            "mode_paiements": tab_mode_paiements,
            "setting": setting,
    }
    return render(request, "edit_inscription.html", context)
    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_in(request): 
    anneeacademique_id = request.session.get('anneeacademique_id') 
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            inscription = Inscription.objects.get(id=id)
        except:
            inscription = None

        if inscription is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else:
            salle_id = request.POST["salle"]
            student_id = request.POST["student"]
            amount = bleach.clean(request.POST["amount"].strip())
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
            amount = amount.replace(" ", "").replace(",", ".")

            try:
                amount = Decimal(amount)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant doit être un nombre valide."})
                
            # Récuperer la salle 
            salle  = Salle.objects.get(id=salle_id)
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont déjà été clôturées."}) 
            if inscription.status_block == False:
                return JsonResponse({
                    "status": "error",
                    "message": "Le compte de cet élève a été définitivement bloqué. Vous ne pouvez donc effectuer aucune opération le concernant."})            
            if salle.price_inscription != amount: # Verifier si le montant corresponds à celui de la salle
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant renseigné ne correspond pas au frais d'inscription de cette salle."})
                
            #On verifie si cette inscription a été déjà enregistrée
            inscriptions = Inscription.objects.exclude(id=id)
            tabSalles = []
            for i in inscriptions: 
                dic = {}  
                dic["anneeacademique_id"] = i.anneeacademique_id
                dic["student_id"] = i.student.id      
                
                tabSalles.append(dic)

            new_dic = {}
            new_dic["anneeacademique_id"] = int(anneeacademique_id)
            new_dic["student_id"] = int(student_id) 
            #On verifie si cette inscription existe déjà
            if new_dic in tabSalles:
                return JsonResponse({
                    "status": "error",
                    "message": "Cette inscription existe déjà."})
            else:
                inscription.salle_id = salle_id
                inscription.student_id = student_id
                inscription.amount = amount
                
                photo = None
                if request.POST.get('photo', True):
                    photo = request.FILES["photo"]
                if photo is not None :
                    inscription.photo = photo
                    
                inscription.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Inscription modifiée avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_inscription(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        inscription_id = int(dechiffrer_param(id))
        inscription = Inscription.objects.get(id=inscription_id)
    except:
        inscription = None
        
    if inscription:
        # Nombre d'inscriptions avant la suppression
        count0 = Inscription.objects.all().count()
        inscription.delete()
        # Nombre d'inscriptions après la suppression
        count1 = Inscription.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("d_inscription", inscription.serieclasse.id)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def inscription_parents(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    inscriptions = Inscription.objects.filter(anneeacademique_id=anneeacademique_id)
    parents = []
    tabParents = []
    for inscription in inscriptions:
        if inscription.student.parent not in tabParents:
            dic = {}
            dic["parent"] = inscription.student.parent
            students = []
            list_students = Student.objects.filter(parent_id=inscription.student.parent.id)
            for student in list_students:
                if Inscription.objects.filter(student_id=student.id, anneeacademique_id=anneeacademique_id).exists():
                    students.append(Inscription.objects.filter(student_id=student.id, anneeacademique_id=anneeacademique_id).first())
            dic["students"] = students
            parents.append(dic)
            tabParents.append(inscription.student.parent)
            
    context = {            
            "parents": parents,
            "setting": setting,
    }
    return render(request, "inscription_parents.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def access_parent(request, id):
    parent = Parent.objects.get(id=id)
    if parent.status_access:
        parent.status_access = False
        parent.save()
        return JsonResponse({
            "status": parent.status_access
        })
    else:
        parent.status_access = True
        parent.save()
        return JsonResponse({
            "status": parent.status_access
        })

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)       
def access_student(request, id):
    inscription = Inscription.objects.get(id=id)
    if inscription.status_access:
        inscription.status_access = False
        inscription.save()
        return JsonResponse({
            "status": inscription.status_access
        })
    else:
        inscription.status_access = True
        inscription.save()
        return JsonResponse({
            "status": inscription.status_access
        })

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)       
def block_account_student(request, id):
    user = request.user
    inscription = Inscription.objects.get(id=id)
    inscription.status_block = False
    inscription.responsable = user
    inscription.save()
    return JsonResponse({
        "status": "success"
    })
        
def ajax_amount_inscription(request, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    salle = Salle.objects.get(id=salle_id)
    context = {
        "setting": setting,
        "amount": salle.price_inscription
    }
    return render(request, "ajax_amount_inscription.html", context)


# ====================== Comptabilité ============================

# Compter le nombre d'élèves inscris dans une salle
def nombre_student_inscris(salle_id, anneeacademique_id):
    nb_inscriptions = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id).count()
    return nb_inscriptions

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def comptabilite_inscription(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_inscriptions = (Inscription.objects.values("salle_id")
                           .filter(anneeacademique_id=anneeacademique_id)
                           .annotate(somme_frais=Sum("amount")))
    
    salles = []
    total = 0
    total_inscris = 0
    for si in salles_inscriptions:
        total += si["somme_frais"] 
        salle = Salle.objects.get(id=si["salle_id"])
        dic = {}
        dic["salle"] = salle
        dic["somme_frais"] = si["somme_frais"]
        nb_student_inscris = nombre_student_inscris(si["salle_id"], anneeacademique_id)
        dic["nb_student_inscris"] = nb_student_inscris
        total_inscris += nb_student_inscris
        
        salles.append(dic)
        
        
    context = {
        "setting": setting,
        "salles": salles,
        "total": total,
        "total_inscris": total_inscris
    }
    return render(request, "comptabilite_inscription.html", context=context)

# Liste des étudiants de la salle de l'eenseignant
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_enseignant)
def inscriptions_enseignant(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    enseignant_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_enseignements = (Enseigner.objects.values("salle_id")
                            .filter(enseignant_id=enseignant_id, anneeacademique_id=anneeacademique_id)
                            .annotate(nombres_matieres=Count("matiere"))
    ) 
    tabSalles = []
    for se in salles_enseignements:
        dic = {}
        salle = Salle.objects.get(id=se["salle_id"])
        dic["salle"] = salle
        inscriptions = Inscription.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id)
        dic["inscriptions"] = inscriptions
        dic["nombres_students"] = inscriptions.count()
        tabSalles.append(dic)
            
    context = {
        "setting": setting,
        "salles": tabSalles,
    }
    return render(request, "inscriptions_enseignant.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_user)
def inscriptions_admin(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_groupes = Inscription.objects.values("salle_id").filter(anneeacademique_id=anneeacademique_id).annotate(nombre_students=Count("student"))
    tabSalle = []
    student_total = 0
    for sg in salles_groupes:
        salle = Salle.objects.get(id=sg["salle_id"])
        dic = {}
        dic["salle"] = salle
        dic["inscriptions"] = Inscription.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id)
        nombre_students = sg["nombre_students"] 
        dic["nombre_students"] = nombre_students
        
        tabSalle.append(dic)
            
        student_total += nombre_students
    
    template = ''    
    if request.session.get('group_name') in permission_DG:
        template = 'global/base_sup_admin.html'
    if request.session.get('group_name') in ["Surveillant Général"]:
        template = 'global/base.html'
            
    context = {
        "setting": setting,
        "salles": tabSalle,
        "student_total": student_total,
        "template": template
    }
    return render(request, "inscriptions_admin.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def attestation_inscription(request, student_id):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    date_actuelle = date.today()
    
    id = int(dechiffrer_param(str(student_id)))
    inscription = Inscription.objects.filter(student_id=id, anneeacademique_id=anneeacademique_id).first()
    # Récuperer l'établissement
    etablissement = Etablissement.objects.get(id=etablissement_id)
    user = None
    for role in EtablissementUser.objects.filter(etablissement=etablissement):
        if role.group.name == "Promoteur":                       
            user = user
            break
                            
    anneeacademique  = AnneeCademique.objects.get(id=anneeacademique_id)
    
    # Chemin vers notre image
    image_path = setting.logo

    # Lire l'image en mode binaire et encoder en Base64
    base64_string = None
    if image_path:
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
    
    context = {
        "user": user,
        "inscription": inscription,      
        "base64_image": base64_string, 
        "setting": setting,
        "date_actuelle": date_actuelle,
        "anneeacademique": anneeacademique,
        'domain':get_current_site(request).domain
    }
    template = get_template("attestation_inscription.html")
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
    }
    pdf = pdfkit.from_string(html, False, options)
    reponse = HttpResponse(pdf, content_type='application/pdf')
    reponse['Content-Disposition'] = f"attachment; filename=Attestion_{ inscription.student.lastname }_{ inscription.student.firstname }.pdf"
    return reponse    
