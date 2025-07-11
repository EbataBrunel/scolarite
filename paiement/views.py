# Importation des modules standards
import bleach
import re
import base64
import pdfkit
import uuid
import requests
import json
# Importation des modules tiers
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.views import View
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from datetime import date
from django.http.response import HttpResponse
from django.template.loader import get_template
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.db import transaction
from datetime import datetime
from django.conf import settings
#from django.urls import reverse
# Importation des modules locaux
from .models import*
from inscription.models import Inscription
from anneeacademique.models import AnneeCademique
from app_auth.models import Parent, Student
from school.utils import send_email_with_html_body
from school.views import get_setting, get_setting_sup_user
from school.methods import format_month, periode_annee_scolaire, debut_month_actuel
from app_auth.decorator import allowed_users, unauthenticated_customer
from scolarite.utils.crypto import chiffrer_param, dechiffrer_param

permission_supuser = ["Super user", "Super admin"]
permission_promoteur_DG = ['Promoteur', 'Directeur Général']
permission_gestionnaire = ['Promoteur', 'Directeur Général', 'Gestionnaire']

# Recuperer les mois aux quels les élèves ont payé dans cette période scolaire
def month_payment(anneeacademique_id):
    tabMonths = []
    months = periode_annee_scolaire(anneeacademique_id) # Récuperer tous les mois de l'année scolaire
    liste_months = debut_month_actuel(anneeacademique_id) # Liste des mois allant du début de la periode de l'année scolaire jusqu'au mois actuel
    
    for  month in months:
        if month in liste_months:
            tabMonths.append(month)
        else:
            if Payment.objects.filter(month=month, anneeacademique_id=anneeacademique_id).exists():
                tabMonths.append(month)
    return tabMonths

# Recuperer les mois aux quels les élèves ont payé allant du mois actuel au dernier mois de la période scolaire
def payment_month_actuel_dernier(anneeacademique_id):
    tabMonths = []
    months = periode_annee_scolaire(anneeacademique_id) # Récuperer tous les mois de l'année scolaire
    liste_months = debut_month_actuel(anneeacademique_id) # Liste des mois allant du début de la periode de l'année scolaire jusqu'au mois actuel
    
    for  month in months:
        if (month in liste_months) or Payment.objects.filter(month=month, anneeacademique_id=anneeacademique_id).exists():
            continue
        else:
            tabMonths.append(month)
    return tabMonths

# Verifier si l'élève à payer tous les mois précèdant aux quels il est autorisé à payer
def payment_next_month(month, salle_id, student_id, anneeacademique_id):
    # Récuperer la période de l'année scolaire
    months = periode_annee_scolaire(anneeacademique_id)
    # Recuperer les mois précédants
    tabmonths = []
    for m in months:
        if m == month:
            break
        else:
            tabmonths.append(m)

    tabnewmonth = []
    for m in tabmonths:
        # Verifier si l'étudiant n'est pas autorisé à payer ce mois
        query_autorisation = AutorisationPayment.objects.filter(salle_id=salle_id, student_id=student_id, anneeacademique_id=anneeacademique_id, month=m)
        # Verifier si les étudiants de cette salle ne sont pas autorisés à payer ce mois 
        query_autorisation_salle = AutorisationPaymentSalle.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id, month=m)
        if query_autorisation_salle.exists() or query_autorisation.exists():
            pass
        else:
            tabnewmonth.append(m)
      
    status_paiement = False       
    for m in tabnewmonth:
        query = Payment.objects.filter(salle_id=salle_id, student_id=student_id, anneeacademique_id=anneeacademique_id, month=m)  
        if query.exists():
            pass
        else:
            status_paiement = True
            break
        
    return status_paiement 

# Verifier si l'établissement à payer tous les mois précèdants aux quels il est autorisé à payer
def payment_next_month_etablissement(month, etablissement_id, anneeacademique_id):
    # Récuperer la période de l'année scolaire
    months = periode_annee_scolaire(anneeacademique_id)
    # Recuperer les mois précédants
    tabmonths = []
    for m in months:
        if m == month:
            break
        else:
            tabmonths.append(m)

    tabnewmonth = []
    for m in tabmonths:
        # Verifier si l'établissement n'est pas autorisé à payer ce mois
        query_autorisation = AutorisationPaymentEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id, month=m)
        if query_autorisation.exists(): pass
        else: tabnewmonth.append(m)
      
    status_paiement = False       
    for m in tabnewmonth:
        query = PaymentEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id, month=m)  
        if query.exists(): pass
        else:
            status_paiement = True
            break
        
    return status_paiement 
# ====================================== Gestion de paiements ======================================

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def payments(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    salles_payments = (Payment.objects.values("salle_id")
                     .filter(anneeacademique_id = anneeacademique_id)
                     .annotate(effectif=Count("salle_id")))
    
    tabSalles = []
    for sp in salles_payments:        
        salle = Salle.objects.get(id=sp["salle_id"])               
        if salle.classe.id == classe_id:
            # Compter le nombre d'étudiants qui ont payé
            students_payments = (Payment.objects.values("student_id")
                                 .filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id)
                                 .annotate(nb_payment=Count('student_id')))
            nb_students = 0
            for st in students_payments:
                nb_students += 1
            dic = {}
            dic["salle"] = salle
            dic["nb_students"] = nb_students
            tabSalles.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "salles": tabSalles,
        "anneeacademique": anneeacademique
    }
    return render(request, "payments.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def students_payments(request, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    id = int(dechiffrer_param(str(salle_id)))
    if setting is None:
        return redirect("settings/maintenance")

    students_payments = (Payment.objects.values("student_id")
                     .filter(anneeacademique_id = anneeacademique_id, salle_id=id)
                     .annotate(nb_payments=Count("student_id")))
    
    tabStudents = []
    for sp in students_payments:        
        student = Student.objects.get(id=sp["student_id"])               
        dic = {}
        dic["student"] = student
        dic["nb_payments"] = sp["nb_payments"]
        tabStudents.append(dic)
                
    salle = Salle.objects.get(id=id)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "students": tabStudents,
        "salle": salle,
        "anneeacademique": anneeacademique
    }
    return render(request, "students_payments.html", context)  

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def detail_payment(request, salle_id, student_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    id_salle = int(dechiffrer_param(str(salle_id)))
    id_student = int(dechiffrer_param(str(student_id)))
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salle = Salle.objects.get(id=id_salle)
    student = Student.objects.get(id=id_student)
    payments = Payment.objects.filter(salle_id=id_salle, student_id=id_student, anneeacademique_id=anneeacademique_id)
    
    # Récuperer tous les mois de l'année académique
    months = periode_annee_scolaire(anneeacademique_id)
    date_actuel = date.today() # date actuelle
    month_actuel = date_actuel.strftime("%m") # Mois actuel
    month_actuel = format_month(month_actuel)
    # Récuperer tous les mois du début de la rentrée jusqu'au mois actuel
    tabMonths = []
    for month in months:
        if month == month_actuel:
            tabMonths.append(month)
            break
        else:
            tabMonths.append(month)
            
    # Récuperer tous les paiements de l'étudiant du début de la rentrée jusqu'à ce jour
    tabMonthPaye = []
    montant_restant = 0
    for month in tabMonths:
        dic = {}
        dic["month"] = month
        # Verifier si l'élève est autoriser à payer ce mois ou pas
        autorisation = AutorisationPayment.objects.filter(salle_id=id_salle, student_id=id_student, month=month, anneeacademique_id=anneeacademique_id)
        # Verifier si les élèves de cette salles sont autorisés à payer ce mois
        query_autorisation_salle = AutorisationPayment.objects.filter(salle_id=id_salle, month=month, anneeacademique_id=anneeacademique_id)
        if autorisation.exists() or query_autorisation_salle.exists():
            dic["status"] = "Ne paye pas"
        else:
            payment = Payment.objects.filter(salle_id=id_salle, student_id=id_student, month=month, anneeacademique_id=anneeacademique_id)
            if payment.exists():
                paye = payment.first()
                if paye.amount < salle.price:
                    dic["status"] = "Avance"
                    montant_restant += (salle.price - paye.amount)
                else:
                    dic["status"] = "Payé"
            else:
                dic["status"] = "Impayé"
                montant_restant += salle.price
                
        tabMonthPaye.append(dic)
    
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)             
    context = {
        "setting": setting,
        "payments": payments,
        "salle": salle,
        "student": student,
        "montant_restant": montant_restant,
        "months_payes" : tabMonthPaye,
        "anneeacademique": anneeacademique
    }
    return render(request, "detail_payment.html", context)
    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_payment(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    classe_id = request.session.get('classe_id')
    if request.method == "POST":

        salle_id = request.POST["salle"]
        student_id = request.POST["student"]
        month = bleach.clean(request.POST["month"].strip())
        amount = bleach.clean(request.POST["amount"].strip())
        
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = amount.replace(" ", "").replace(",", ".")

        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
         
        paiements = Payment.objects.filter(salle_id=salle_id, student_id=student_id, anneeacademique_id=anneeacademique_id)   
        for payment in paiements:
            # Recupérer la salle
            salle = Salle.objects.get(id=salle_id)
            if payment.amount < salle.price:
                return JsonResponse({
                    "status": "error",
                    "message": "Completez d'abord les frais d'un mois avant d'effectuer un nouveau paiement."})
        
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
        # Verifier si l'étudiant est autorisé à payer ce mois ou pas
        query_autorisation = AutorisationPayment.objects.filter(salle_id=salle_id, student_id=student_id, anneeacademique_id=anneeacademique_id, month=month)
        # Verifier si les étudiants ne sont pas autorisés à payer ce mois pour cette salle
        query_autorisation_salle = AutorisationPaymentSalle.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id, month=month)
        query = Payment.objects.filter(salle_id=salle_id, student_id=student_id, anneeacademique_id=anneeacademique_id, month=month) 
        # Récuperer l'inscription de l'étudiant
        inscription = Inscription.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id).first()               
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."})
        if inscription.status_block == False:
            return JsonResponse({
                "status": "error",
                "message": "Le compte de cet élève a été définitivement bloqué. Vous ne pouvez donc effectuer aucune opération le concernant."})     
        if query_autorisation_salle.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Les étudiants ne pas autorisés à payer ce mois pour cette salle."})
        if query_autorisation.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cet élève n'est pas autorisé à payer ce mois."})
            
        if payment_next_month(month, salle_id, student_id, anneeacademique_id): 
            return JsonResponse({
                    "status": "error",
                    "message": "Il existe au moins un mois précédent que cet élève n'a pas encore payé."})
            
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Ce paiement existe déjà."})
        else:
            payment = Payment(
                salle_id=salle_id, 
                student_id=student_id, 
                user_id=user_id, 
                month=month, 
                amount=amount, 
                anneeacademique_id=anneeacademique_id)
            
            # Nombre de paiement avant l'ajout
            count0 = Payment.objects.all().count()
            payment.save()
            # Nombre de paiements après l'ajout
            count1 = Payment.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Paiement enregistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Le paiement a échoué."})

    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id)
    months = periode_annee_scolaire(anneeacademique_id)
    mode_paiements = ["Espèce", "Virement", "Mobile"]
    context = {
        "setting": setting,
        "salles": salles,
        "months": months,
        "mode_paiements": mode_paiements
    }
    return render(request, "add_payment.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_payment(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    payment_id = int(dechiffrer_param(str(id)))
    payment = Payment.objects.get(id=payment_id)
        
    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id).exclude(id=payment.salle.id)
    # Recuperer tous les étudints de cette salle
    inscriptions = Inscription.objects.filter(salle_id=payment.salle.id, anneeacademique_id=anneeacademique_id)
    students = [inscription.student for inscription in inscriptions if payment.student.id != inscription.student.id]
    
    months = periode_annee_scolaire(anneeacademique_id)
    tabMonths = [month for month in months if month != months]

    mode_paiements = ["Espèce", "Virement", "Mobile"]
    tab_mode_paiements = [mode_paiement for mode_paiement in mode_paiements if mode_paiement != payment.mode_paiement]
    
    context = {
        "setting": setting,
        "payment": payment,
        "salles": salles,
        "students": students,
        "months": tabMonths,
        "mode_paiements": tab_mode_paiements
    }
    return render(request, "edit_payment.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_py(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            payment = Payment.objects.get(id=id)
        except:
            payment = None

        if payment is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            salle_id = request.POST["salle"]
            student_id = request.POST["student"]
            month = bleach.clean(request.POST["month"].strip())
            amount = bleach.clean(request.POST["amount"].strip())
            
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
            amount = amount.replace(" ", "").replace(",", ".")

            try:
                amount = Decimal(amount)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant doit être un nombre valide."})
                
            # Verifier l'existence du paiement
            payments = Payment.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).exclude(id=id)
            tabPayments = []
            for p in payments:
                dic = {}
                dic["salle_id"] = p.salle.id
                dic["student_id"] = p.student.id
                dic["month"] = p.month 
                
                tabPayments.append(dic)
            
            new_dic = {}
            new_dic["salle_id"] = int(salle_id)
            new_dic["student_id"] = int(student_id)  
            new_dic["month"] = month 
            
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
            # Verifier si l'étudiant est autorisé à payer ce mois ou pas
            query_autorisation = AutorisationPayment.objects.filter(salle_id=salle_id, student_id=student_id, anneeacademique_id=anneeacademique_id, month=month)
            # Verifier si les étudiants ne sont pas autorisés à payer ce mois pour cette salle
            query_autorisation_salle = AutorisationPaymentSalle.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id, month=month)
            # Récuperer l'inscription de l'étudiant
            inscription = Inscription.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id).first()        
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."})
            if inscription.status_block == False:
                return JsonResponse({
                    "status": "error",
                    "message": "Le compte de cet élève a été définitivement bloqué. Vous ne pouvez donc effectuer aucune opération le concernant."})     
            if query_autorisation_salle.exists():
                return JsonResponse({
                        "status": "error",
                        "message": "Les étudiants ne pas autorisés à payer ce mois pour cette salle."})
            if query_autorisation.exists():
                return JsonResponse({
                        "status": "error",
                        "message": "Cet élève n'est pas autorisé à payer ce mois."})
            
            if new_dic in tabPayments:
                return JsonResponse({
                    "status": "error",
                    "message": "Ce paiement existe déjà."}) 
            else:
                payment.salle_id = salle_id
                payment.student_id = student_id
                payment.month = month
                payment.amount = amount
                payment.user_id = user_id
                payment.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Paiement modifié avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_payment(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        payment_id = int(dechiffrer_param(str(id)))
        payment = Payment.objects.get(id=payment_id)
    except:
        payment = None
        
    if payment:
        # Nombre de paiements avant la suppression
        count0 = Payment.objects.all().count()
        payment.delete()
        # Nombre de paiements après la suppression
        count1 = Payment.objects.all().count()
        if count1 < count0: 
            messages.success(request, "ELément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("detail_payment", payment.salle.id, payment.student.id)


#============================ Gestion des autorisations de payments ==================================
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def autorisation_payments(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    salles_authorisations = (AutorisationPayment.objects.values("salle_id")
                     .filter(anneeacademique_id = anneeacademique_id)
                     .annotate(nb_etudiants=Count("salle_id")))
    
    tabSalles = []
    for sp in salles_authorisations:        
        salle = Salle.objects.get(id=sp["salle_id"])               
        if salle.classe.id == classe_id:
            # Compter le nombre d'étudiants qui ne sont pas autorisés à payer
            nb_students = (AutorisationPayment.objects.values("student_id")
                                 .filter(anneeacademique_id = anneeacademique_id, salle_id=salle.id)
                                 .aggregate(Count('student_id'))['student_id__count'] or 0)        
            dic = {}
            dic["salle"] = salle
            dic["nb_students"] = nb_students
            tabSalles.append(dic)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "salles": tabSalles,
        "anneeacademique": anneeacademique
    }
    return render(request, "autorisation/autorisation_payments.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def detail_autorisation_payments(request, salle_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    id = int(dechiffrer_param(str(salle_id)))
    students_autorisations = (AutorisationPayment.objects.values("student_id")
                     .filter(anneeacademique_id=anneeacademique_id, salle_id=id)
                     .annotate(nb_autorisations=Count("student_id")))
    
    tabStudents = []
    for sp in students_autorisations:        
        student = Student.objects.get(id=sp["student_id"])               
        dic = {}
        dic["student"] = student
        dic["nb_autorisations"] = sp["nb_autorisations"]
        dic["autorisations"] = AutorisationPayment.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=id, student_id=student.id)
        tabStudents.append(dic)
                
    salle = Salle.objects.get(id=id)
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "students": tabStudents,
        "salle": salle,
        "anneeacademique": anneeacademique
    }
    return render(request, "autorisation/detail_autorisation_payments.html", context)
    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_autorisation_payment(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    classe_id = request.session.get('classe_id')
    if request.method == "POST":

        salle_id = request.POST["salle"]
        student_id = request.POST["student"]
        month = bleach.clean(request.POST["month"].strip())
        justification = bleach.clean(request.POST["justification"].strip())
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id) 
        query = AutorisationPayment.objects.filter(salle_id=salle_id, student_id=student_id, anneeacademique_id=anneeacademique_id, month=month) 
        # Récuperer l'inscription de l'étudiant
        inscription = Inscription.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id).first()                      
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
            return JsonResponse({
                "status": "error",
                "message": "Les opérations de cette année académique ont été déjà clôturées."})
        if inscription.status_block == False:
            return JsonResponse({
                "status": "error",
                "message": "Le compte de cet élève a été définitivement bloqué. Vous ne pouvez donc effectuer aucune opération le concernant."})     
        if query.exists():
            return JsonResponse({
                "status": "error",
                "message": "Cette autorisation de paiement existe déjà."})
        else:
            autorisation = AutorisationPayment(
                salle_id=salle_id, 
                student_id=student_id, 
                user_id=user_id, 
                month=month, 
                justification=justification, 
                anneeacademique_id=anneeacademique_id)
            
            # Nombre d'autorisations avant l'ajout
            count0 = AutorisationPayment.objects.all().count()
            autorisation.save()
            # Nombre d'autorisations après l'ajout
            count1 = AutorisationPayment.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Autorisation enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'autorisation a échouée."})

    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id)
    months = periode_annee_scolaire(anneeacademique_id)
    context = {
        "setting": setting,
        "salles": salles,
        "months": months
    }
    return render(request, "autorisation/add_autorisation_payment.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_autorisation_payment(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    autorisation_id = int(dechiffrer_param(str(id)))
    autorisation = AutorisationPayment.objects.get(id=autorisation_id)
        
    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id).exclude(id=autorisation.salle.id)
    # Recuperer tous les étudints de cette salle
    inscriptions = Inscription.objects.filter(salle_id=autorisation.salle.id, anneeacademique_id=anneeacademique_id)
    students = [inscription.student for inscription in inscriptions if autorisation.student.id != inscription.student.id]
    
    
    months = periode_annee_scolaire(anneeacademique_id)
    tabMonths = [month for month in months if month != months]

    context={
        "setting": setting,
        "autorisation": autorisation,
        "salles": salles,
        "students": students,
        "months": tabMonths
    }
    return render(request, "autorisation/edit_autorisation_payment.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_ap(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            autorisation = AutorisationPayment.objects.get(id=id)
        except:
            autorisation = None

        if autorisation is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            salle_id = request.POST["salle"]
            student_id = request.POST["student"]
            month = bleach.clean(request.POST["month"].strip())
            justification = bleach.clean(request.POST["justification"].strip())
             
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)   
            # Récuperer l'inscription de l'étudiant
            inscription = Inscription.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id).first()                
            # Verifier l'existence du paiement
            autorisations = AutorisationPayment.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).exclude(id=id)
            tabAutorisations = []
            for p in autorisations:
                dic = {}
                dic["salle_id"] = p.salle.id
                dic["student_id"] = p.student.id
                dic["month"] = p.month 
                
                tabAutorisations.append(dic)
            
            new_dic = {}
            new_dic["salle_id"] = int(salle_id)
            new_dic["student_id"] = int(student_id)  
            new_dic["month"] = month 
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."})
            if inscription.status_block == False:
                return JsonResponse({
                    "status": "error",
                    "message": "Le compte de cet élève a été définitivement bloqué. Vous ne pouvez donc effectuer aucune opération le concernant."})     
            if new_dic in tabAutorisations:
                return JsonResponse({
                    "status": "error",
                    "message": "Cette autorisation de paiement existe déjà."}) 
            else:
                autorisation.salle_id = salle_id
                autorisation.student_id = student_id
                autorisation.month = month
                autorisation.justification = justification
                autorisation.user_id = user_id
                autorisation.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Autorisation de paiement modifiée avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_autorisation_payment(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        authorisation_id = int(dechiffrer_param(str(id)))
        authorisation = AutorisationPayment.objects.get(id=authorisation_id)
    except:
        authorisation = None
        
    if authorisation:
        # Nombre d'autorisations avant la suppression
        count0 = AutorisationPayment.objects.all().count()
        authorisation.delete()
        # Nombre de d'autorisations après la suppression
        count1 = AutorisationPayment.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
        
        return redirect("autorisation/detail_autorisation_payments", authorisation.salle.id)

def ajax_delete_autorisation_student(request, id):
    autorisation = AutorisationPayment.objects.get(id=id)
    context = {
        "autorisation": autorisation
    }
    return render(request, "ajax_delete_autorisation_student.html", context)

# ====================================== Gestion d'autorisation de paiements d'une salle  
@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def autorisation_payments_salle(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    salles_authorisations = (AutorisationPaymentSalle.objects.values("salle_id")
                     .filter(anneeacademique_id=anneeacademique_id)
                     .annotate(nb_etudiants=Count("salle_id")))
    
    tabSalles = []
    for sp in salles_authorisations:        
        salle = Salle.objects.get(id=sp["salle_id"])               
        if salle.classe.id == classe_id:
            # Compter le nombre d'étudiants qui ne sont pas autorisés à payer
            nb_months = (AutorisationPaymentSalle.objects.values("month")
                                 .filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id)
                                 .aggregate(Count('month'))['month__count'] or 0)        
            dic = {}
            dic["salle"] = salle
            dic["nb_months"] = nb_months
            dic["autorisations"] = AutorisationPaymentSalle.objects.filter(anneeacademique_id = anneeacademique_id, salle_id=salle.id)
            tabSalles.append(dic)

    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id) 
    context = {
        "setting": setting,
        "salles": tabSalles,
        "anneeacademique": anneeacademique
    }
    return render(request, "autorisation_paye_salle/autorisation_payments_salle.html", context)
    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def add_autorisation_payment_salle(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    user_id = request.user.id
    classe_id = request.session.get('classe_id')
    if request.method == "POST":

        salle_id = request.POST["salle"]
        month = bleach.clean(request.POST["month"].strip())
        justification = bleach.clean(request.POST["justification"].strip())
        # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
        anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)  
        query = AutorisationPaymentSalle.objects.filter(salle_id=salle_id, anneeacademique_id=anneeacademique_id, month=month)        
        if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."})
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette autorisation de paiement de la salle existe déjà."})
        else:
            autorisation = AutorisationPaymentSalle(
                salle_id=salle_id,  
                user_id=user_id, 
                month=month, 
                justification=justification, 
                anneeacademique_id=anneeacademique_id)
            
            # Nombre d'autorisations avant l'ajout
            count0 = AutorisationPaymentSalle.objects.all().count()
            autorisation.save()
            # Nombre d'autorisations après l'ajout
            count1 = AutorisationPaymentSalle.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Autorisation de paiement de la salle enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'autorisation a échouée."})

    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id)
    months = periode_annee_scolaire(anneeacademique_id)
    context = {
        "setting": setting,
        "salles": salles,
        "months": months
    }
    return render(request, "autorisation_paye_salle/add_autorisation_payment_salle.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_autorisation_payment_salle(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    classe_id = request.session.get('classe_id')
    autorisation_id = int(dechiffrer_param(str(id)))
    autorisation = AutorisationPaymentSalle.objects.get(id=autorisation_id)
        
    salles = Salle.objects.filter(classe_id=classe_id, anneeacademique_id=anneeacademique_id).exclude(id=autorisation.salle.id)
    
    months = periode_annee_scolaire(anneeacademique_id)
    tabMonths = [month for month in months if month != months]
    context = {
        "setting": setting,
        "autorisation": autorisation,
        "salles": salles,
        "months": tabMonths
    }
    return render(request, "autorisation_paye_salle/edit_autorisation_payment_salle.html", context)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def edit_aps(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            autorisation = AutorisationPaymentSalle.objects.get(id=id)
        except:
            autorisation = None

        if autorisation is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            salle_id = request.POST["salle"]
            month = bleach.clean(request.POST["month"].strip())
            justification = bleach.clean(request.POST["justification"].strip())
             
            # Récuperer la délibération pour verifier si ses activités ont été cloturées ou pas
            anneescolaire = AnneeCademique.objects.filter(status_cloture=False, id=anneeacademique_id)    
            # Verifier l'existence du paiement
            autorisations = AutorisationPaymentSalle.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id).exclude(id=id)
            tabAutorisations = []
            for p in autorisations:
                dic = {}
                dic["salle_id"] = p.salle.id
                dic["month"] = p.month 
                
                tabAutorisations.append(dic)
            
            new_dic = {}
            new_dic["salle_id"] = int(salle_id)
            new_dic["month"] = month 
            if anneescolaire.exists(): # Verifier si on a déjà cloturé les opérations de cette année
                return JsonResponse({
                    "status": "error",
                    "message": "Les opérations de cette année académique ont été déjà clôturées."})
            if new_dic in tabAutorisations:
                return JsonResponse({
                    "status": "error",
                    "message": "Cette autorisation de paiement de la salle existe déjà."}) 
            else:
                autorisation.salle_id = salle_id
                autorisation.month = month
                autorisation.justification = justification
                autorisation.user_id = user_id
                autorisation.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Autorisation de paiement de la salle modifiée avec succès."})

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_gestionnaire)
def del_autorisation_payment_salle(request,id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    try:
        authorisation_id = int(dechiffrer_param(str(id)))
        authorisation = AutorisationPaymentSalle.objects.get(id=authorisation_id)
    except:
        authorisation = None
        
    if authorisation:
        # Nombre d'autorisations de paiements avant la suppression
        count0 = AutorisationPaymentSalle.objects.all().count()
        authorisation.delete()
        # Nombre d'autorisations de paiements après la suppression
        count1 = AutorisationPaymentSalle.objects.all().count()
        if count1 < count0: 
            messages.success(request, "ELément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("autorisation_paye_salle/autorisation_payments_salle")

def ajax_delete_autorisation_salle(request, id):
    autorisation = AutorisationPaymentSalle.objects.get(id=id)
    context = {
        "autorisation": autorisation
    }
    return render(request, "ajax_delete_autorisation_salle.html", context)

class get_student_inscris_salle(View):
    def get(self, request, id, *args, **kwargs):
        anneeacademique_id = request.session.get('anneeacademique_id')
        inscriptions = Inscription.objects.filter(salle_id=id, anneeacademique_id=anneeacademique_id)
        students = []
        for inscription in inscriptions:
            students.append(inscription.student)
            
        context = {
            "students": students
        }
        return render(request, "ajax_student_inscris.html", context)

# =========================== Gestion des contrats ================================    
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def contrat_etablissements(request):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    contrats = ContratEtablissement.objects.filter(anneeacademique_id=anneeacademique_id)

    context = {
        "setting": setting,
        "contrats": contrats
    }
    return render(request, "contrat_etablissement/contrat_etablissements.html", context)    

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def add_contrat_etablissement(request):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    user_id = request.user.id
    if request.method == "POST":
        etablissement_id = request.POST["etablissement"]
        description = bleach.clean(request.POST["description"].strip())
        amount = bleach.clean(request.POST["amount"].strip())
        start_date = bleach.clean(request.POST["start_date"].strip())
        end_date = bleach.clean(request.POST["end_date"].strip())
        
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = amount.replace(" ", "").replace(",", ".")

        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
        
        query = ContratEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id)
        if query.exists():
                return JsonResponse({
                        "status": "error",
                        "message": "Ce contrat existe déjà."})
        else:
            contrat = ContratEtablissement(
                    user_id=user_id, 
                    description=description,
                    amount=amount,
                    anneeacademique_id=anneeacademique_id,
                    etablissement_id=etablissement_id,
                    start_date=start_date,
                    end_date=end_date
            )
            # Nombre de contrats avant l'ajout
            count0 = ContratEtablissement.objects.all().count()
            contrat.save()
            # Nombre de contrats après l'ajout
            count1 = ContratEtablissement.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                            "status": "success",
                            "message": "Contrat enregistré avec succès."})
            else:
                return JsonResponse({
                            "status": "error",
                            "message": "Insertion a échouée."})
                
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    etablissements = Etablissement.objects.all()
    tabEtablissement = []
    for e in etablissements:
        if AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement_id=e.id).exists():
            tabEtablissement.append(e)

    context = {
        "setting": setting,
        "etablissements": tabEtablissement
    }
    return render(request, "contrat_etablissement/add_contrat_etablissement.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def edit_contrat_etablissement(request,id):
    setting = get_setting_sup_user()
    contrat_id = int(dechiffrer_param(str(id)))
    contrat = ContratEtablissement.objects.get(id=contrat_id)    
    etablissements = Etablissement.objects.exclude(id=contrat.etablissement.id)
    tabEtablissement = []
    for e in etablissements:
        if AnneeCademique.objects.filter(etablissement_id=e.id).exists():
            tabEtablissement.append(e)
            
    context = {
        "setting": setting,
        "etablissements": tabEtablissement,
        "contrat": contrat
    }
    return render(request, "contrat_etablissement/edit_contrat_etablissement.html", context)
   

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def edit_ce(request):
    anneeacademique_id = request.session.get('annee_id')
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            contrat = ContratEtablissement.objects.get(id=id)
        except:
            contrat = None

        if contrat is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            etablissement_id = request.POST["etablissement"]
            description = bleach.clean(request.POST["description"].strip())
            amount = bleach.clean(request.POST["amount"].strip())
            start_date = bleach.clean(request.POST["start_date"].strip())
            end_date = bleach.clean(request.POST["end_date"].strip())
            
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
            amount = amount.replace(" ", "").replace(",", ".")

            try:
                amount = Decimal(amount)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant doit être un nombre valide."})
            # Vérifier l'existence du contrat
            contrats = ContratEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id).exclude(id=id)
            tabContrat = []
            for c in contrats:   
                dic = {}
                dic["etablissement_id"] = c.etablissement.id
                dic["anneeacademique_id"] = c.anneeacademique.id
                tabContrat.append(dic)            
                
            new_dic = {}
            new_dic["etablissement_id"] = int(etablissement_id)
            new_dic["anneeacademique_id"] = int(anneeacademique_id)
            
            if new_dic in tabContrat: # Vérifier l'existence du programme
                return JsonResponse({
                    "status": "error",
                    "message": "Ce contrat existe déjà."})
            else:
                contrat.user_id = request.user.id
                contrat.description = description
                contrat.amount = amount
                contrat.etablissement_id=etablissement_id
                contrat.start_date=start_date
                contrat.end_date=end_date
                contrat.save()
                
                return JsonResponse({
                    "status": "success",
                    "message": "Contrat modifié avec succès."})


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def del_contrat_etablissement(request, id):
    contrat_id = int(dechiffrer_param(str(id)))
    contrat = ContratEtablissement.objects.get(id=contrat_id)
    # Nombre de contrats avant la suppression
    count0 = ContratEtablissement.objects.all().count()
    contrat.delete()
    # Nombre de contrats après la suppression
    count1 = ContratEtablissement.objects.all().count()
    if count1 < count0: 
        messages.success(request, "Elément supprimé avec succès.")
    else:
        messages.error(request, "La suppression a échouée.")
    return redirect("contrat_etablissement/contrat_etablissements")

def ajax_delete_contrat_etablissement(request, id):
    contrat = ContratEtablissement.objects.get(id=id)
    context = {
        "contrat": contrat
    }
    return render(request, "ajax_delete_contrat_etablissement.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def mes_contrats_superuser(request):
    
    user_id = request.user.id
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    contrats = ContratEtablissement.objects.filter(anneeacademique_id=anneeacademique_id).order_by("-id")
    tabcontrats = []
    for contrat in contrats: 
        if contrat.etablissement.promoteur.id == user_id:
            tabcontrats.append(contrat)

    context = {
            "setting": setting,
            "contrats": tabcontrats
    }
    return render(request, "contrat_etablissement/mes_contrats_supuser.html", context)
    

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=["Promoteur", "Directeur Général"])
def mes_contrats_promoteur(request):
    setting_supuser = get_setting_sup_user()
    user_id = request.user.id
    anneeacademique_id = request.session.get('anneeacademique_id')
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    setting = get_setting(anneeacademique_id)
    contrats = ContratEtablissement.objects.all().order_by("-id")
    tabcontrats = []
    for contrat in contrats: 
        if contrat.anneeacademique.annee_debut == anneeacademique.annee_debut and contrat.anneeacademique.annee_fin == anneeacademique.annee_fin and contrat.etablissement.promoteur.id == user_id:
            tabcontrats.append(contrat)

    context = {
            "setting": setting,
            "setting_supuser": setting_supuser,
            "contrats": tabcontrats
    }
    return render(request, "contrat_etablissement/mes_contrats_promoteur.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def signer_contrat_promoteur(request, contrat_id):
    try:
        contrat = ContratEtablissement.objects.get(id=contrat_id)
        contrat.status_signature = True
        contrat.date_signature = date.today()
        contrat.save()
    except:
        contrat = None
    
    context = {
        "contrat": contrat
    }
    return render(request, "signer_mon_contrat.html", context)

def ajax_dates_etablissement(request, id):
    anneeacademique_id = request.session.get('annee_id')
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    anneeacademique_etablissement = AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement_id=id).first()
    context = {
        "anneeacademique": anneeacademique_etablissement
    }
    return render(request, "ajax_dates_etablissement.html", context)
    
#============================ Gestion des autorisations de payments des établissements ==================================
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def autorisation_paye_etablissements(request):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    
    etablissements_autorisations = (AutorisationPaymentEtablissement.objects.values("etablissement_id")
                     .filter(anneeacademique_id=anneeacademique_id)
                     .annotate(nombre_months=Count("etablissement_id")))
    
    etablissements = []
    for ea in etablissements_autorisations:        
        etablissement = Etablissement.objects.get(id=ea["etablissement_id"])               
        dic = {}
        dic["etablissement"] = etablissement
        dic["nombre_months"] = ea["nombre_months"]
        dic["autorisations"] = AutorisationPaymentEtablissement.objects.filter(etablissement_id=etablissement.id, anneeacademique_id=anneeacademique_id) 
        etablissements.append(dic)

    context = {
        "setting": setting,
        "etablissements": etablissements
    }
    return render(request, "autorisation_paye_etablissement/autorisation_paye_etablissements.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def add_autorisation_paye_etablissement(request):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    user_id = request.user.id
    if request.method == "POST":

        etablissement_id = request.POST["etablissement"]
        month = bleach.clean(request.POST["month"].strip())
        justification = bleach.clean(request.POST["justification"].strip())
        query = AutorisationPaymentEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id, month=month)        

        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cette autorisation de paiement existe déjà."})
        else:
            autorisation = AutorisationPaymentEtablissement(
                etablissement_id=etablissement_id, 
                user_id=user_id, 
                month=month, 
                justification=justification, 
                anneeacademique_id=anneeacademique_id)
            
            # Nombre d'autorisations avant l'ajout
            count0 = AutorisationPaymentEtablissement.objects.all().count()
            autorisation.save()
            # Nombre d'autorisations après l'ajout
            count1 = AutorisationPaymentEtablissement.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Autorisation enregistrée avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "L'autorisation a échouée."})

    etablissements = Etablissement.objects.all()
    tabEtablissement = []
    for e in etablissements:
        if AnneeCademique.objects.filter(etablissement_id=e.id).exists():
            tabEtablissement.append(e)
            
    months = periode_annee_scolaire(anneeacademique_id)
    context={
        "setting": setting,
        "etablissements": tabEtablissement,
        "months": months
    }
    return render(request, "autorisation_paye_etablissement/add_autorisation_paye_etablissement.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def edit_autorisation_paye_etablissement(request,id):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()

    autorisation_id = int(dechiffrer_param(str(id)))
    autorisation = AutorisationPaymentEtablissement.objects.get(id=autorisation_id)
        
    etablissements = Etablissement.objects.exclude(id=autorisation.etablissement.id)
    tabEtablissement = []
    for e in etablissements:
        if AnneeCademique.objects.filter(etablissement_id=e.id).exists():
            tabEtablissement.append(e)
    
    months = periode_annee_scolaire(anneeacademique_id)
    tabMonths = [month for month in months if month != months]
    
    context = {
        "setting": setting,
        "autorisation": autorisation,
        "etablissements": etablissements,
        "months": tabMonths
    }
    return render(request, "autorisation_paye_etablissement/edit_autorisation_paye_etablissement.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def edit_ae(request):
    anneeacademique_id = request.session.get('annee_id')
    user_id = request.user.id
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            autorisation = AutorisationPaymentEtablissement.objects.get(id=id)
        except:
            autorisation = None

        if autorisation is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            etablissement_id = request.POST["etablissement"]
            month = bleach.clean(request.POST["month"].strip())
            justification = bleach.clean(request.POST["justification"].strip())
  
            # Verifier l'existence du paiement
            autorisations = AutorisationPaymentEtablissement.objects.filter(anneeacademique_id=anneeacademique_id, etablissement_id=etablissement_id).exclude(id=id)
            tabAutorisations = []
            for p in autorisations:
                dic = {}
                dic["etablissement_id"] = p.etablissement.id
                dic["month"] = p.month 
                
                tabAutorisations.append(dic)
            
            new_dic = {}
            new_dic["etablissement_id"] = int(etablissement_id)  
            new_dic["month"] = month 
            if new_dic in tabAutorisations:
                return JsonResponse({
                    "status": "error",
                    "message": "Cette autorisation de paiement existe déjà."}) 
            else:
                autorisation.etablissement_id = etablissement_id
                autorisation.month = month
                autorisation.justification = justification
                autorisation.user_id = user_id
                autorisation.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Autorisation de paiement modifiée avec succès."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def del_autorisation_paye_etablissement(request, id):
    try:
        authorisation_id = int(dechiffrer_param(str(id)))
        authorisation = AutorisationPaymentEtablissement.objects.get(id=authorisation_id)
    except:
        authorisation = None
        
    if authorisation:
        # Nombre d'autorisations avant la suppression
        count0 = AutorisationPaymentEtablissement.objects.all().count()
        authorisation.delete()
        # Nombre de d'autorisations après la suppression
        count1 = AutorisationPaymentEtablissement.objects.all().count()
        if count1 < count0: 
            messages.success(request, "Elément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
        
        return redirect("autorisation_paye_etablissement/autorisation_paye_etablissements")

def ajax_delete_autorisation_paye_etablissement(request, id):
    autorisation = AutorisationPaymentEtablissement.objects.get(id=id)
    context = {
        "autorisation": autorisation
    }
    return render(request, "ajax_delete_autorisation_paye_etablissement.html", context)
    
# ====================== Gestion de paiement des établissements ============================
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def payment_etablissements(request):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    etablissements_groupes = (PaymentEtablissement.objects.values("etablissement_id")
                              .filter(anneeacademique_id=anneeacademique_id)
                              .annotate(nombre_payments=Count("etablissement_id"))
    )
    etablissements = []
    for eg in etablissements_groupes:
        dic = {}
        etablissement = Etablissement.objects.get(id=eg["etablissement_id"])
        dic["etablissement"] = etablissement
        dic["nombre_payments"] = eg["nombre_payments"]
        dic["nombre_nouvaux_payments"] = etablissement.payment_etablissements.filter(anneeacademique_id=anneeacademique_id, status=False).count()
        dic["payments"] = etablissement.payment_etablissements.filter(anneeacademique_id=anneeacademique_id)
        etablissements.append(dic)
        
    context = {
        "setting": setting,
        "etablissements": etablissements
    }
    return render(request, "payment_etablissement/payment_etablissements.html", context)

# Création de User API
def user_api(unique_ref, subscription_key):
    url = "https://sandbox.momodeveloper.mtn.com/v1_0/apiuser"
    headers = {
        'X-Reference-Id': unique_ref,  # ID unique de la transaction
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/json'
    }
    data = {
        "providerCallbackHost": "string"
    }
    # Elle retourne 201 si l'opération a reussi 
    response = requests.post(url, data=json.dumps(data), headers=headers)

    return response.status_code

def generate_momo_api_key(unique_ref, subscription_key):
    url = f"https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/{unique_ref}/apikey"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/json'
    }
    body = {"providerCallbackHost": "string"}

    response = requests.post(url, data=json.dumps(body), headers=headers)

    if response.status_code == 201:
        user_key_tojson = response.json()
        apikey = user_key_tojson['apiKey']
        print("Clé API générée avec succès:", apikey)
        return apikey
    else:
        print("Erreur lors de la génération de la clé API:", response.json())
        return None

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def mes_payment_etablissement(request):
    
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer tous les mois de l'année académique
    months = periode_annee_scolaire(anneeacademique_id)
    date_actuel = date.today() # date actuelle
    month_actuel = date_actuel.strftime("%m") # Mois actuel
    month_actuel = format_month(month_actuel)
    # Récuperer tous les mois du début de la rentrée jusqu'au mois actuel
    tabMonths = []
    for month in months:
        if month == month_actuel:
            tabMonths.append(month)
            break
        else:
            tabMonths.append(month)
    
    #Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    anneeacademique_etablissement = AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement=None).first()
    payments = []
    for month in tabMonths:
        query = PaymentEtablissement.objects.filter(etablissement_id=etablissement_id, month=month, anneeacademique_id=anneeacademique_etablissement.id)
        if query.exists():
            payment = query.first()
            dic = {}
            dic["month"] = payment.month
            dic["number_student"] = payment.number_student
            dic["amount_student"] = payment.amount_student
            dic["amount"] = payment.amount
            if payment.status:
                dic["status"] = "Payé"
            else:
                dic["status"] = "En cours"
            payments.append(dic)
        else:
            query_auto = AutorisationPaymentEtablissement.objects.filter(etablissement_id=etablissement_id, month=month, anneeacademique_id=anneeacademique_etablissement.id)
            if query_auto.exists(): continue
            else:
                dic = {}
                dic["month"] = month
                # Fonction qui determine le nombre d'etudiant, le montant à payer par étudiant et l montant total
                nombre_student, montant_student, montant_total = nombre_montant_total(anneeacademique_etablissement.id, etablissement_id, month)
                dic["number_student"] = nombre_student
                dic["amount_student"] = montant_student
                dic["amount"] = montant_total
                dic["status"] = "Impayé"
                payments.append(dic)
    context = {
        "setting": setting,
        "payments": payments
    }
    return render(request, "payment_etablissement/mes_payment_etablissement.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def validate_payment_etablissement(request, month):
    
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    mont = dechiffrer_param(month)
    unique_ref = str(uuid.uuid4())
    subscription_key = settings.MTN_PRIMARY_KEY
    if request.method == "POST":
            month = bleach.clean(request.POST["month"].strip())
            amount = bleach.clean(request.POST["amount"].strip())
            phone_number = bleach.clean(request.POST["phone"].strip())
            
            user_api(unique_ref, subscription_key)
            
            apikey = generate_momo_api_key(unique_ref, subscription_key)
                              
            url = "https://sandbox.momodeveloper.mtn.com/collection/token/"
            hdr = {'Ocp-Apim-Subscription-Key': subscription_key}
            r = requests.post(url, headers=hdr, auth=(unique_ref, apikey))
            if r.status_code == 200:
                json_content = r.json()
                access_token = json_content['access_token']
                token_type = json_content['token_type']
                expires_in = json_content['expires_in']
                print('access_token : ', access_token),
                print('token_type :', token_type),
                print('expires_in :', expires_in)
                
                # Transaction
                
                headers = {
                    'Authorization': f"Bearer {access_token}",
                    'X-Reference-Id': unique_ref,  # Utilisez un identifiant unique pour chaque requête
                    'X-Target-Environment': 'sandbox',  # Changez en 'production' si vous passez en production
                    'Ocp-Apim-Subscription-Key': subscription_key,
                    'Content-Type': 'application/json'
                }
                body = {
                    "amount": amount,
                    "currency": "EUR",
                    "externalId": "123456789",
                    "payer": {
                        "partyIdType": "MSISDN",
                        "partyId": phone_number
                    },
                    "payerMessage": "Paiement pour votre commande",
                    "payeeNote": "Merci pour votre paiement"
                }

                ul = 'https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay'
                response = requests.post(ul, data=json.dumps(body), headers=headers)
                print(response.status_code)
                if response.status_code == 500:
                    transaction_id = unique_ref  # Utilisez `unique_ref` pour suivre le statut
                    return redirect("payment_etablissement/payment_successful", transaction_id, chiffrer_param(mont))
                else:
                    #print(response.json())  # Affiche le message d'erreur détaillé
                    return redirect("payment_etablissement/payment_etablissement_echec")
                    #return JsonResponse({"status": "error", "message": "Transaction échouée"})
            else:
                #print(response.json())  # Affiche le message d'erreur détaillé
                return redirect("payment_etablissement/payment_etablissement_echec")
                #return JsonResponse({"status": "error", "message": "Transaction échouée"})
    
    #Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    anneeacademique_etablissement = AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement=None).first()
    number_student, amount_student, amount = nombre_montant_total(anneeacademique_etablissement.id, etablissement_id, mont)
    context = {
        "setting": setting,
        "month": mont,
        "number_student": number_student,
        "amount_student": amount_student,
        "amount": amount
    }
    return render(request, "payment_etablissement/validate_payment_etablissement.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
@transaction.atomic
def payment_successful(request, transaction_id, month):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    mont = dechiffrer_param(month)
    # Récuperer l'année académique de l'établissement
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique du group  
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement=None).first()
    number_student, amount_student, amount = nombre_montant_total(anneeacademique_group.id, etablissement_id, mont)
   
    # Enregistrer le paiement 
    payment = PaymentEtablissement(
                etablissement_id=etablissement_id, 
                number_student=number_student, 
                amount_student=amount_student,
                amount=amount, 
                month=mont,
                mode_payment="Mobile",
                anneeacademique_id=anneeacademique_group.id,
                transaction_id=transaction_id,
                user_id=user_id
    )
    payment.save() 
    return redirect("payment_etablissement/payment_etablissement_success", month)


@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
@transaction.atomic
def payment_etablissement_success(request, month):
    etablissement_id = request.session.get('etablissement_id')
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    mont = dechiffrer_param(month)

    date = datetime.now()
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    # Récuperer l'année académique du groupe
    anneeacademique_group = AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement_id=None).first()
    setting_group = get_setting_sup_user()
    # Recuperer le paiement
    payment = PaymentEtablissement.objects.filter(etablissement_id=etablissement_id, month=mont, anneeacademique_id=anneeacademique_group.id).first()
    
    subject = "Paiement des frais du site de l'établissement"
    template = "email/email_paiement_etablissement.html"
    receivers = [request.user.email]
    # Recuperer le membre qui a effectué l'achat
    user = User.objects.get(id=request.user.id)            
    ctxt = {
        "user": user,
        "payment": payment,
        'date': date,
        'setting': setting,
        'setting_group': setting_group,
        "domain":get_current_site(request).domain,
    }

    send_email_with_html_body(
        subjet=subject,
        receivers=receivers,
        template=template,
        context=ctxt
    )
    
    context = {
        "payment": payment,
        "setting": setting
    }
    return render(request, "payment_etablissement/payment_etablissement_success.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def payment_etablissement_echec(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    context = {
        "setting": setting
    }
    return render(request, "payment_etablissement/payment_etablissement_echec.html", context)
    
@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def add_payment_etablissement(request):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    
    user_id = request.user.id
    if request.method == "POST":

        etablissement_id = request.POST["etablissement"]
        mode_payment = request.POST["mode_payment"]
        number_student = request.POST["number_student"]
        amount_student = bleach.clean(request.POST["amount_student"].strip())
        amount = bleach.clean(request.POST["amount"].strip())
        month = bleach.clean(request.POST["month"].strip())
        
        # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
        amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
        amount = amount.replace(" ", "").replace(",", ".")

        amount_student = re.sub(r'\xa0', '', amount_student)  # Supprime les espaces insécables
        amount_student = amount_student.replace(" ", "").replace(",", ".")
        
        try:
            amount_student = Decimal(amount_student)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant par élève doit être un nombre valide."})
            
        try:
            amount = Decimal(amount)  # Convertir en Decimal
        except:
            return JsonResponse({
                "status": "error",
                "message": "Le montant doit être un nombre valide."})
        
        """ 
        paiements = PaymentEtablissement.objects.filter(etablissement_id=etablissement_id, month=month, anneeacademique_id=anneeacademique_id)   
        for payment in paiements:
            # Recupérer la salle
            salle = Salle.objects.get(id=salle_id)
            if payment.amount < salle.price:
                return JsonResponse({
                    "status": "error",
                    "message": "Completez d'abord les frais d'un mois avant d'effectuer un nouveau paiement."})"""

        # Verifier si l'étudiant est autorisé à payer ce mois ou pas
        query_autorisation = AutorisationPaymentEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id, month=month)
        query = PaymentEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id, month=month)        
        if int(number_student) == 0:
            return JsonResponse({
                    "status": "error",
                    "message": "Le nombre d'élève doit être superieur à 0."})
        
        if query_autorisation.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Cet établissement n'est pas autorisé à payer ce mois."})
            
        if payment_next_month_etablissement(month, etablissement_id, anneeacademique_id): 
            return JsonResponse({
                    "status": "error",
                    "message": "Il existe au moins un mois précédent celui-ci que cet établissement n'a pas payé."})
            
        if query.exists():
            return JsonResponse({
                    "status": "error",
                    "message": "Ce paiement existe déjà."})
        else:
            payment = PaymentEtablissement(
                etablissement_id=etablissement_id, 
                number_student=number_student, 
                amount_student=amount_student,
                amount=amount, 
                month=month,
                mode_payment=mode_payment,
                anneeacademique_id=anneeacademique_id,
                status=True,
                user_id=user_id)
            
            # Nombre de paiement avant l'ajout
            count0 = PaymentEtablissement.objects.all().count()
            payment.save()
            # Nombre de paiements après l'ajout
            count1 = PaymentEtablissement.objects.all().count()
            # On verifie si l'insertion a eu lieu ou pas.
            if count0 < count1:
                return JsonResponse({
                    "status": "success",
                    "message": "Paiement enregistré avec succès."})
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Le paiement a échoué."})

    # Récuperer l'année académique 
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    etablissements = Etablissement.objects.all()
    tabEtablissement = []
    # On récupere que les établissements qui ont signé le contrat pour cette année
    for e in etablissements:
        if AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement_id=e.id).exists() and ContratEtablissement.objects.filter(etablissement_id=e.id, status_signature=True, anneeacademique_id=anneeacademique_id).exists():
            tabEtablissement.append(e)
            
    mode_paiements = ["Espèce", "Virement", "Mobilene"]
    context = {
        "setting": setting,
        "etablissements": tabEtablissement,
        "mode_paiements": mode_paiements
    }
    return render(request, "payment_etablissement/add_payment_etablissement.html", context)

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def edit_payment_etablissement(request,id):
    anneeacademique_id = request.session.get('annee_id')
    setting = get_setting_sup_user()
    payment_id = int(dechiffrer_param(str(id)))
    payment = PaymentEtablissement.objects.get(id=payment_id)
        
    etablissements = Etablissement.objects.filter().exclude(id=payment.etablissement.id)
    tabEtablissement = []
    for e in etablissements:
        if AnneeCademique.objects.filter(etablissement_id=e.id).exists() and ContratEtablissement.objects.filter(etablissement_id=e.id, status_signature=True, anneeacademique_id=anneeacademique_id).exists():
            tabEtablissement.append(e)
    
    months = periode_annee_scolaire(anneeacademique_id)
    tabMonths = [month for month in months if month != months]

    mode_paiements = ["Espèce", "Virement", "Mobile"]
    tab_mode_paiements = [mode_paiement for mode_paiement in mode_paiements if mode_paiement != payment.mode_payment]
    
    context = {
        "setting": setting,
        "payment": payment,
        "etablissements": tabEtablissement,
        "months": tabMonths,
        "mode_paiements": tab_mode_paiements
    }
    return render(request, "payment_etablissement/edit_payment_etablissement.html", context)


@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def edit_pe(request):
    anneeacademique_id = request.session.get('annee_id')
    user_id = request.user.id
    if request.method == "POST":
        id = int(request.POST["id"])
        try:
            payment = PaymentEtablissement.objects.get(id=id)
        except:
            payment = None

        if payment is None:
            return JsonResponse({
                    "status": "error",
                    "message": "Identifiant inexistant."})
        else: 
            etablissement_id = request.POST["etablissement"]
            month = bleach.clean(request.POST["month"].strip())
            number_student = bleach.clean(request.POST["number_student"].strip())
            amount_student = bleach.clean(request.POST["amount_student"].strip())
            amount = bleach.clean(request.POST["amount"].strip())
            
            # Nettoyer la valeur (supprimer les espaces et remplacer la virgule par un point)
            amount = re.sub(r'\xa0', '', amount)  # Supprime les espaces insécables
            amount = amount.replace(" ", "").replace(",", ".")
            
            amount_student = re.sub(r'\xa0', '', amount_student)  # Supprime les espaces insécables
            amount_student = amount_student.replace(" ", "").replace(",", ".")

            try:
                amount_student = Decimal(amount_student)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant par élève doit être un nombre valide."})
                
            try:
                amount = Decimal(amount)  # Convertir en Decimal
            except:
                return JsonResponse({
                    "status": "error",
                    "message": "Le montant doit être un nombre valide."})
                
            # Verifier l'existence du paiement
            payments = PaymentEtablissement.objects.filter(anneeacademique_id=anneeacademique_id, etablissement_id=etablissement_id).exclude(id=id)
            tabPayments = []
            for p in payments:
                dic = {}
                dic["etablissement_id"] = p.etablissement.id
                dic["month"] = p.month 
                
                tabPayments.append(dic)
            
            new_dic = {}
            new_dic["etablissement_id"] = int(etablissement_id)
            new_dic["month"] = month 
            
            # Verifier si l'établissement est autorisé à payer ce mois
            query_autorisation = AutorisationPaymentEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id, month=month)
            if int(number_student) == 0:
                return JsonResponse({
                    "status": "error",
                    "message": "Le nombre d'élève doit être superieur à 0."})
            if query_autorisation.exists():
                return JsonResponse({
                        "status": "error",
                        "message": "Cet établissement n'est pas autorisé à payer ce mois."})
            
            if new_dic in tabPayments:
                return JsonResponse({
                    "status": "error",
                    "message": "Ce paiement existe déjà."}) 
            else:
                payment.etablissement_id = etablissement_id
                payment.number_student = number_student
                payment.amount_student = amount_student
                payment.month = month
                payment.amount = amount
                payment.user_id = user_id
                payment.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Paiement modifié avec succès."})

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def del_payment_etablissement(request, id):
    
    try:
        payment_id = int(dechiffrer_param(str(id)))
        payment = PaymentEtablissement.objects.get(id=payment_id)
    except:
        payment = None
        
    if payment:
        # Nombre de paiements avant la suppression
        count0 = PaymentEtablissement.objects.all().count()
        payment.delete()
        # Nombre de paiements après la suppression
        count1 = PaymentEtablissement.objects.all().count()
        if count1 < count0: 
            messages.success(request, "ELément supprimé avec succès.")
        else:
            messages.error(request, "La suppression a échouée.")
    return redirect("payment_etablissement/payment_etablissements")

def ajax_delete_payment_etablissement(request, id):
    payment = PaymentEtablissement.objects.get(id=id)
    context = {
        "payment": payment
    }
    return render(request, "ajax_delete_payment_etablissement.html", context)

# Récuperer le mois et l'année de la période scolaire
def month_year_periode_annee_scolaire(anneeacademique_id):
    try:
        anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    except ObjectDoesNotExist:
        return []  # Retourne une liste vide si l'année académique n'existe pas

    start_date = anneeacademique.start_date
    end_date = anneeacademique.end_date

    # Génération des mois dans l'intervalle
    months = []
    current_date = start_date.replace(day=1)  # S'assurer de commencer au début du mois

    while current_date <= end_date:
        dic = {} 
        dic["month"] = current_date.strftime("%m")
        dic["year"] = current_date.strftime("%Y")
        months.append(dic)
        # Passer au mois suivant
        next_month = current_date.month % 12 + 1
        next_year = current_date.year + (1 if current_date.month == 12 else 0)
        current_date = current_date.replace(month=next_month, year=next_year)

    month_format = []
    for month in months:
        if month["month"] == '01':
            dic = {}
            dic["month"] = "Janvier"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '02':
            dic = {}
            dic["month"] = "Février"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '03':
            dic = {}
            dic["month"] = "Mars"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '04':
            dic = {}
            dic["month"] = "Avril"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '05':
            dic = {}
            dic["month"] = "Mai"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '06':
            dic = {}
            dic["month"] = "Juin"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '07':
            dic = {}
            dic["month"] = "Juillet"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month == '08':
            dic = {}
            dic["month"] = "Août"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '09':
            dic = {}
            dic["month"] = "Septembre"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '10':
            dic = {}
            dic["month"] = "Octobre"
            dic["year"] = month["year"]
            month_format.append(dic)
        elif month["month"] == '11':
            dic = {}
            dic["month"] = "Novembre"
            dic["year"] = month["year"]
            month_format.append(dic)
        else:
            dic = {}
            dic["month"] = "Décembre"
            dic["year"] = month["year"]
            month_format.append(dic)
    return month_format  # Retourne la liste des mois

def quinze_month(month, anneeacademique_id):
    MOIS_FR = {
        'Janvier': 1,
        'Février': 2,
        'Mars': 3,
        'Avril': 4,
        'Mai': 5,
        'Juin': 6,
        'Juillet': 7,
        'Août': 8,
        'Septembre': 9,
        'Octobre': 10,
        'Novembre': 11,
        'Décembre': 12
    }
    
    # Récuperer le mois et l'année de la période scolaire
    months = month_year_periode_annee_scolaire(anneeacademique_id)
    mois = ""
    annee = 0
    for m in months:
        if m["month"] == month: 
            mois = month
            annee = m["year"]
            break
        
    mois_num = MOIS_FR[mois]
    # Crée la date du 15 du mois dans la même année
    date_quinze = date(int(annee), mois_num, 15)

    return date_quinze

# Fonction qui determine le nombre d'etudiant, le montant à payer par étudiant et l montant total
def nombre_montant_total(anneeacademique_id, etablissement_id, month):
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    etablissement = Etablissement.objects.get(id=etablissement_id)
    anneeacademique_etablissement = AnneeCademique.objects.filter(
        annee_debut=anneeacademique.annee_debut, 
        annee_fin=anneeacademique.annee_fin, 
        etablissement_id=etablissement.id).first()
    # Récuperer les inscriptions de l'établissement
    nombre_students = 0
    inscriptions = Inscription.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_etablissement.id)
    for inscription in inscriptions:
        if inscription.status_block:
            if inscription.dateins.date() <= quinze_month(month, anneeacademique_id):
                nombre_students += 1
        else:
            if inscription.date_block.date() <= quinze_month(month, anneeacademique_id):
                nombre_students += 1

    #Récuperer le contrat de l'établissement
    contrat = ContratEtablissement.objects.filter(etablissement_id=etablissement_id, anneeacademique_id=anneeacademique_id).first()
    montant_student = 0
    montant = 0
    if contrat:
        # Montant que chaque étudiant paye par mois
        montant_student = float(contrat.amount)
        # Calculer le montant
        montant = nombre_students * montant_student    
    return nombre_students, montant_student, montant

def ajax_amount_contrat_etablissement(request, etablissement_id, month):
    setting = get_setting_sup_user()
    anneeacademique_id = request.session.get('annee_id')
    
    nombre_students, montant_student, montant = nombre_montant_total(anneeacademique_id, etablissement_id, month)
    context = {
        "nombre_students": nombre_students,
        "montant_student": montant_student,
        "montant": montant,
        "setting": setting
    }
    return render(request, "ajax_amount_contrat_etablissement.html", context)


def ajax_month_payment_etablissement(request, id):
    anneeacademique_id = request.session.get('annee_id')
    # Récuperer l'année académique
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    etablissement = Etablissement.objects.get(id=id)
    anneeacademique_etablissement = AnneeCademique.objects.filter(
        annee_debut=anneeacademique.annee_debut, 
        annee_fin=anneeacademique.annee_fin, 
        etablissement_id=etablissement.id).first()
    
    months = periode_annee_scolaire(anneeacademique_etablissement.id)
    context = {
       "months": months 
    }
    return render(request, "ajax_month_payment_etablissement.html", context)

def ajax_modal_confirmation_payment(request, id):
    payment = PaymentEtablissement.objects.get(id=id)
    context = {
        "payment": payment
    }
    return render(request, "ajax_modal_confirmation_payment.html", context)

@login_required(login_url='connection/login') 
@allowed_users(allowed_roles=permission_supuser)
def confirmation_payment(request, id):
    payment = PaymentEtablissement.objects.get(id=id)
    payment.status = True
    payment.save()
    
    # Nombre de nouveaux paiements
    number_new_payments = PaymentEtablissement.objects.filter(etablissement=payment.etablissement, status=False, anneeacademique=payment.anneeacademique).count()
    return JsonResponse({
        "status": payment.status,
        "number_new_payments": number_new_payments,
        "etablissement_id": payment.etablissement.id
    })

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)    
def payments_months_etablissement(request):
    anneeacademique_id = request.session.get('annee_id')
    # Récuperer l'année académique du groupe
    anneeacademique = AnneeCademique.objects.get(id=anneeacademique_id)
    setting = get_setting_sup_user()
    months = debut_month_actuel(anneeacademique_id)
    payments = []
    for month in months:
        dic = {}
        dic["month"] = month
        etablissements = Etablissement.objects.all()
        nombre_etablissements = 0
        tabEtablissements = []
        montant_total = 0
        montant_encaisse = 0
        for etablissement in etablissements:
            new_dic = {}
            if AnneeCademique.objects.filter(annee_debut=anneeacademique.annee_debut, annee_fin=anneeacademique.annee_fin, etablissement=etablissement).exists():
                if AutorisationPaymentEtablissement.objects.filter(etablissement=etablissement, anneeacademique=anneeacademique, month=month).exists(): continue
                else:
                   nombre_etablissements += 1
                   new_dic["etablissement"] = etablissement
                   nombre_students, montant_student, montant = nombre_montant_total(anneeacademique_id, etablissement.id, month)
                   new_dic["nombre_students"] = nombre_students
                   new_dic["montant_student"] = montant_student
                   new_dic["montant"] = montant
                   if PaymentEtablissement.objects.filter(etablissement=etablissement, anneeacademique=anneeacademique, month=month).exists():
                       montant_encaisse += montant
                       new_dic["status"] = "Payé"
                   else:
                       new_dic["status"] = "Impayé"
                   montant_total += montant
            tabEtablissements.append(new_dic)
        dic["montant_total"] = montant_total
        dic["montant_encaisse"] = montant_encaisse
        dic["montant_restant"] = float(montant_total) - float(montant_encaisse)
        dic["etablissements"] = tabEtablissements
        dic["nombre_etablissements"] = nombre_etablissements
        payments.append(dic)
       
    context = {
      "setting": setting,  
      "payments": payments
    }
    return render(request, "payment_etablissement/payments_months_etablissement.html", context)

@login_required(login_url='connection/account')
@allowed_users(allowed_roles=permission_promoteur_DG)
def recu_paye_etablissement(request, id):
    setting = get_setting_sup_user()
    payment_id = int(dechiffrer_param(str(id)))
    payment = PaymentEtablissement.objects.get(id=payment_id)       
    # Récuperer l'année académique du grapupe                   
    anneeacademique  = AnneeCademique.objects.get(id=payment.anneeacademique.id)
    # Chemin vers notre image
    image_path = setting.logo
    
    # Lire l'image en mode binaire et encoder en Base64
    base64_string = ""
    if image_path:
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
    # Date actuelle
    date_actuelle = date.today()
    
    context = {
        "etablisemnet": payment.etablissement,
        "payment": payment,      
        "base64_image": base64_string, 
        "setting": setting,
        "anneeacademique": anneeacademique,
        "date_actuelle": date_actuelle
    }
    template = get_template("recu_paye_etablissement.html")
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
    }
    pdf = pdfkit.from_string(html, False, options)
    reponse = HttpResponse(pdf, content_type='application/pdf')
    reponse['Content-Disposition'] = f"attachment; filename=Recu_{ payment.etablissement.name }_{ payment.etablissement.name }.pdf"
    return reponse

@login_required(login_url='connection/login')
@allowed_users(allowed_roles=permission_supuser)
def comptabilite_supuser(request):
    setting = get_setting_sup_user()
    anneeacademique_id = request.session.get('annee_id')
    payments_groups = (PaymentEtablissement.objects.values("month")
                       .filter(anneeacademique_id=anneeacademique_id)
                       .annotate(nombre_payments=Count("etablissement_id"))
    )
    payments = []
    totale = 0
    for pg in payments_groups:
        dic = {}
        dic["month"] = pg["month"]
        dic["payments"] = PaymentEtablissement.objects.filter(month=pg["month"], anneeacademique_id=anneeacademique_id)
        somme_totale = (PaymentEtablissement.objects.filter(month=pg["month"], anneeacademique_id=anneeacademique_id).aggregate(Sum("amount"))["amount__sum"] or 0)
        dic["somme_totale"] = somme_totale
        totale += somme_totale
        payments.append(dic)
        
    context = {
        "setting": setting,
        "payments": payments,
        "totale": totale
    }
    return render(request, "payment_etablissement/comptabilite_supuser.html", context)

# ====================== Comptabilité ============================

# Compter le nombre d'élèves inscris dans une salle
def nombre_student_inscris(salle_id, anneeacademique_id):
    nb_inscriptions = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id).count()
    return nb_inscriptions

# Somme de paiement par mois
def summ_payment_month(anneeacademique_id, salle_id, month):
    somme_payment = (Payment.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id, month=month)
                            .aggregate(Sum("amount"))["amount__sum"])
    if somme_payment:
        return somme_payment
    else:
        return ""
       
# Somme total de paiement par mois de toutes les salles 
def summ_total_payment_month_all_sall(anneeacademique_id, month):
    
    salles = Salle.objects.filter(anneeacademique_id=anneeacademique_id)
    total = 0
    for salle in salles:
        somme = (Payment.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id, month=month)
                                .aggregate(Sum('amount'))['amount__sum'] or 0)
        total = total + somme
    
    return total  

# Compter le nombre d'élèves inscris et qui doivent payé ce mois
def nombre_student_inscris_paye_month(salle_id, month, anneeacademique_id):
    inscriptions = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle_id)
    nb_inscriptions = 0
    for inscription in inscriptions:
        query = AutorisationPayment.objects.filter(salle_id=salle_id, student_id=inscription.student.id, month=month, anneeacademique_id=anneeacademique_id)
        if not query.exists():
            nb_inscriptions += 1
    return nb_inscriptions

# Somme total que les étudiants doivent payer par mois dans chaque salle 
def summ_total_a_payer_month_all_sall(anneeacademique_id, month):
    
    salles = Salle.objects.filter(anneeacademique_id=anneeacademique_id)
    total = 0
    for salle in salles:
        if not AutorisationPaymentSalle.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id, month=month).exists():
            total = total + salle.price * nombre_student_inscris_paye_month(salle.id, month, anneeacademique_id)
    
    return total      
            
@login_required(login_url='connection/account') 
@allowed_users(allowed_roles=permission_gestionnaire)   
def comptabilite_payment(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    salles_payments = Salle.objects.filter(anneeacademique_id=anneeacademique_id).order_by("classe_id")
    salles = []
    total = 0
    total_inscris = 0
    # Récuperer la période de l'année scolaire
    months = periode_annee_scolaire(anneeacademique_id)
    # Recuperer les mois aux quels les élèves ont payé allant du mois actuel au dernier mois de la période scolaire
    tab_month_payments = payment_month_actuel_dernier(anneeacademique_id)
    for salle in salles_payments:
        somme_frais = (Payment.objects.filter(salle_id=salle.id, anneeacademique_id=anneeacademique_id).aggregate(Sum("amount"))["amount__sum"] or 0)
        total += somme_frais
        dic = {}
        dic["salle"] = salle
        dic["somme_frais"] = somme_frais
        # Récuperer le nombre d'étudiant inscris dans une salle
        nb_student_inscris = nombre_student_inscris(salle.id, anneeacademique_id)
        dic["nb_student_inscris"] = nb_student_inscris
        total_inscris += nb_student_inscris 
        total_amounts = []
        total_restant = 0 # Total restant dans une salle pendant plusieurs mois  
        for month in months:
            # Verifier si les étudiants sont autorisés à payer ce mois pour cette salle
            if AutorisationPaymentSalle.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id, month=month).exists():
                dic_amount = {}
                dic_amount["total_mensuel"] = 0
                dic_amount["total_mensuel_restant"] = 0
                dic_amount["nb_student_paye"] = 0
                dic_amount["nb_student_no_paye"] = 0
                       
                total_amounts.append(dic_amount)
            else:
                # Récuperer le nombre d'étudiant qui doivent payer ce mois
                nb_student_a_payer_month = nombre_student_inscris_paye_month(salle.id, month, anneeacademique_id)
                if month not in tab_month_payments: # Verifier si ce mois ne vient pas après le mois actuel           
                    dic_amount = {}
                    # somme total de frais d'un mois
                    total_mensuel = summ_payment_month(anneeacademique_id, salle.id, month)
                    if total_mensuel:
                        dic_amount["total_mensuel"] = total_mensuel
                    else:
                        dic_amount["total_mensuel"] = 0
                    # Calculer le nombre d'étudiants qui ont payé
                    nb_student_paye = (Payment.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id, month=month)
                                    .aggregate(Count("student_id"))["student_id__count"])
                    dic_amount["nb_student_paye"] = nb_student_paye
                    dic_amount["nb_student_no_paye"] = nb_student_a_payer_month - nb_student_paye
                    # Calucler le montant restant des étudiant pour un mois
                    if total_mensuel:
                        total_mensuel_restant = float(salle.price * nb_student_a_payer_month) - float(total_mensuel)
                        dic_amount["total_mensuel_restant"] = total_mensuel_restant
                        total_restant += total_mensuel_restant
                    else:
                        total_mensuel_restant = float(salle.price * nb_student_a_payer_month)
                        dic_amount["total_mensuel_restant"] = total_mensuel_restant
                        total_restant += total_mensuel_restant
                        
                    total_amounts.append(dic_amount)
                else:
                    if Payment.objects.filter(month=month, anneeacademique_id=anneeacademique_id).exists():
                        dic_amount = {}
                        # somme total de frais d'un mois
                        total_mensuel = summ_payment_month(anneeacademique_id, salle.id, month)
                        if total_mensuel:
                            dic_amount["total_mensuel"] = total_mensuel
                        else:
                            dic_amount["total_mensuel"] = 0
                        # Calculer le nombre d'étudiants qui ont payé
                        nb_student_paye = (Payment.objects.filter(anneeacademique_id=anneeacademique_id, salle_id=salle.id, month=month)
                                        .aggregate(Count("student_id"))["student_id__count"])
                        dic_amount["nb_student_paye"] = nb_student_paye
                        dic_amount["nb_student_no_paye"] = nb_student_a_payer_month - nb_student_paye
                        # Calucler le montant restant des étudiant pour un mois
                        if total_mensuel:
                            total_mensuel_restant = float(salle.price * nb_student_inscris) - float(total_mensuel)
                            dic_amount["total_mensuel_restant"] = total_mensuel_restant
                            total_restant += total_mensuel_restant
                        else:
                            total_mensuel_restant = float(salle.price * nb_student_inscris)
                            dic_amount["total_mensuel_restant"] = total_mensuel_restant
                            total_restant += total_mensuel_restant
                            
                        total_amounts.append(dic_amount)
                    else:
                        dic_amount = {}
                        dic_amount["total_mensuel"] = 0
                        dic_amount["total_mensuel_restant"] = 0
                        dic_amount["nb_student_paye"] = 0
                        dic_amount["nb_student_no_paye"] = 0
                        
                        total_amounts.append(dic_amount)
            
            
        dic["total_restant"] = float(total_restant)    
        dic["total_amounts"] = total_amounts   
        salles.append(dic)
    
    # Somme totale par mois de toutes les salles 
    sommes_totales = []   
    reste_total = 0
    for month in months:
        if month in tab_month_payments:
            if Payment.objects.filter(anneeacademique_id=anneeacademique_id, month=month).exists():
                    dic = {}
                    # Somme total que les étudiants ont payé par mois dans chaque salle
                    total_all_sall = summ_total_payment_month_all_sall(anneeacademique_id, month)
                    dic["total"] = total_all_sall
                    # Somme total que les étudiants doivent payer dans chaque salle
                    total_a_payer_all_sall =  summ_total_a_payer_month_all_sall(anneeacademique_id, month)
                    reste = float(total_a_payer_all_sall) - float(total_all_sall)
                    dic["total_restant"] = reste
                    
                    reste_total += reste
                    
                    sommes_totales.append(dic)
            else:
                dic = {}
                dic["total"] = 0
                dic["total_restant"] = 0
                sommes_totales.append(dic)
        else:
            
            dic = {}
            # Somme total que les étudiants ont payé par mois dans chaque salle
            total_all_sall = summ_total_payment_month_all_sall(anneeacademique_id, month)
            dic["total"] = total_all_sall
            # Somme total que les étudiants doivent payer dans chaque salle
            total_a_payer_all_sall =  summ_total_a_payer_month_all_sall(anneeacademique_id, month)
            reste = float(total_a_payer_all_sall) - float(total_all_sall)
            #print(total_a_payer_all_sall)
            dic["total_restant"] = reste     
            
            reste_total += reste    
            sommes_totales.append(dic)
      
    context = {
        "setting": setting,
        "salles": salles,
        "total": total,
        "reste_total": reste_total,
        "sommes_totales": sommes_totales,
        "months": months,
        "total_inscris": total_inscris
    }
    return render(request, "comptabilite_payment.html", context)

@unauthenticated_customer
def dossier_financier(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    student_id = request.session.get('student_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).first()
    payments = Payment.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student_id).order_by("id")
    
    for payment in payments:
        # Mise à jour du statut pour marquer la lecture du paiement
        payment.status = True
        payment.save()
        
    # Récuperer tous les mois de l'année académique
    months = periode_annee_scolaire(anneeacademique_id)
    date_actuel = date.today() # date actuelle
    month_actuel = date_actuel.strftime("%m") # Mois actuel
    month_actuel = format_month(month_actuel)
    # Récuperer tous les mois du début de la rentrée jusqu'au mois actuel
    tabMonths = []
    for month in months:
        if month == month_actuel:
            tabMonths.append(month)
            break
        else:
            tabMonths.append(month)
            
    # Récuperer tous les paiements de l'étudiant du début de la rentrée jusqu'à ce jour
    tabMonthPaye = []
    montant_restant = 0
    for month in tabMonths:
        dic = {}
        dic["month"] = month
        # Verifier s'il est autoriser à payer ce mois ou pas
        autorisation = AutorisationPayment.objects.filter(salle_id=inscription.salle.id, student_id=student_id, month=month, anneeacademique_id=anneeacademique_id)
        # Verifier si les élèves de cette salles sont autorisés à payer ce mois
        query_autorisation_salle = AutorisationPayment.objects.filter(salle_id=inscription.salle.id, month=month, anneeacademique_id=anneeacademique_id)
        if autorisation.exists() or query_autorisation_salle.exists():
            dic["status"] = "Ne paye pas"
        else:
            payment = Payment.objects.filter(salle_id=inscription.salle.id, student_id=student_id, month=month, anneeacademique_id=anneeacademique_id)
            if payment.exists():
                paye = payment.first()
                if paye.amount < inscription.salle.price:
                    dic["status"] = "Avance"
                    montant_restant += (inscription.salle.price - paye.amount)
                else:
                    dic["status"] = "Payé"
            else:
                dic["status"] = "Impayé"
                montant_restant += inscription.salle.price
                
        tabMonthPaye.append(dic)
    
    context = {
        "setting": setting,
        "inscription": inscription,
        "payments": payments,
        "months": tabMonthPaye,
        "montant_restant": montant_restant
    }
    return render(request, "dossier_financier.html", context=context)

@unauthenticated_customer
def dossier_financier_parent(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    parent_id = request.session.get('parent_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    # Récuperer les enfants du parent
    students = Student.objects.filter(parent_id=parent_id) 
    # Selectionner les enfants du parent qui sont inscris cette année
    tabinscription = []
    for student in students:
        query = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=student.id)
        if query.exists():
            # Récuperer l'inscription
            inscription = query.first()
            tabinscription.append(inscription)
    
    dette_totale = 0
    liste_payments = []
    for i in tabinscription:
        dic = {}
        inscription = Inscription.objects.filter(anneeacademique_id=anneeacademique_id, student_id=i.student.id).first()
        dic["inscription"] = inscription
        payments = Payment.objects.filter(anneeacademique_id=anneeacademique_id, student_id=i.student.id).order_by("id")
        dic["nombre_payes"] = payments.count()
        tabPayments = []
        i = 0
        for payment in payments:
            i += 1
            new_dic = {}
            new_dic["i"] = i
            new_dic["payment"] = payment
            
            tabPayments.append(new_dic)
            # Mise à jour du statut pour marquer la lecture du paiement
            payment.status_parent = True
            payment.save()
            
        dic["payments"] = tabPayments
        
        # Récuperer tous les mois de l'année académique
        months = periode_annee_scolaire(anneeacademique_id)
        date_actuel = date.today() # date actuelle
        month_actuel = date_actuel.strftime("%m") # Mois actuel
        month_actuel = format_month(month_actuel)
        # Récuperer tous les mois du début de la rentrée jusqu'au mois actuel
        tabMonths = []
        for month in months:
            if month == month_actuel:
                tabMonths.append(month)
                break
            else:
                tabMonths.append(month)
                
        # Récuperer tous les paiements de l'étudiant du début de la rentrée jusqu'à ce jour
        montant_restant = 0
        for month in tabMonths:
            # Verifier s'il est autoriser à payer ce mois ou pas
            autorisation = AutorisationPayment.objects.filter(salle_id=inscription.salle.id, student_id=inscription.student.id, month=month, anneeacademique_id=anneeacademique_id)
            # Verifier si les étudiants de cette salle ne sont pas autorisés à payer ce mois
            query_autorisation = AutorisationPaymentSalle.objects.filter(salle_id=inscription.salle.id, month=month, anneeacademique_id=anneeacademique_id)
            if autorisation.exists() or query_autorisation.exists():
                pass
            else:
                payment = Payment.objects.filter(salle_id=inscription.salle.id, student_id=inscription.student.id, month=month, anneeacademique_id=anneeacademique_id)
                if payment.exists():
                    paye = payment.first()
                    if paye.amount < inscription.salle.price:
                        montant_restant += (inscription.salle.price - paye.amount)
                else:
                    montant_restant += inscription.salle.price
            
        dic["montant_restant"] = montant_restant
        
        liste_payments.append(dic)
        
        dette_totale += montant_restant
    
    context = {
        "setting": setting,
        "inscription": inscription,
        "payments": liste_payments,
        "dette_totale": dette_totale
    }
    return render(request, "dossier_financier_parent.html", context)

@login_required(login_url='connection/account') 
@allowed_users(allowed_roles=permission_gestionnaire)
def recu_paye(request, id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    paiement_id = int(dechiffrer_param(str(id)))
    paiement = Payment.objects.get(id=paiement_id)
    user = None
    users = User.objects.all()
    for user in users:
        if user.groups.exists():
            groups = user.groups.all()
            for group in groups:
                    if group.name in ["Gestionnaire"]:                       
                            user = user
                            
    anneeacademique  = AnneeCademique.objects.get(id=anneeacademique_id)
    
    # Chemin vers notre image
    image_path = setting.logo
    
    # Lire l'image en mode binaire et encoder en Base64
    base64_string = ""
    if image_path:
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
    # Date actuelle
    date_actuelle = date.today()
    
    context = {
        "user": user,
        "paiement": paiement,      
        "base64_image": base64_string, 
        "setting": setting,
        "anneeacademique": anneeacademique,
        "date_actuelle": date_actuelle
    }
    template = get_template("recu_paye.html")
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
    }
    pdf = pdfkit.from_string(html, False, options)
    reponse = HttpResponse(pdf, content_type='application/pdf')
    reponse['Content-Disposition'] = f"attachment; filename=Recu_{ paiement.student.lastname }_{ paiement.student.firstname }.pdf"
    return reponse 
        
@unauthenticated_customer
def echeancier(request, student_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    
    st_id = int(dechiffrer_param(str(student_id)))
    inscription = Inscription.objects.filter(student_id=st_id, anneeacademique_id=anneeacademique_id).first()
    anneeacademique  = AnneeCademique.objects.get(id=anneeacademique_id)
    
    # Chemin vers notre image
    image_path = setting.logo

    # Lire l'image en mode binaire et encoder en Base64
    base64_string = None
    if image_path:
        base64_string = base64.b64encode(image_path.read()).decode('utf-8')
    # Date actuelle
    date_actuelle = date.today()
    
    paiements = Payment.objects.filter(student_id=st_id, anneeacademique_id=anneeacademique_id)
    
    montant_total = (Payment.objects.filter(student_id=st_id, anneeacademique_id=anneeacademique_id)
                     .aggregate(Sum("amount"))["amount__sum"]) or 0
    
    total = float(montant_total) + float(inscription.amount)
          
    context = {
        "paiements": paiements,
        "inscription": inscription,
        "base64_image": base64_string,
        "total": total,
        "setting": setting,
        "anneeacademique": anneeacademique,
        "date_actuelle": date_actuelle
    }
    template = get_template("echeancier.html")
    html = template.render(context)
    options = {
        'page-size': 'Letter',
        'encoding': "UTF-8",
    }
    pdf = pdfkit.from_string(html, False, options)
    reponse = HttpResponse(pdf, content_type='application/pdf')
    reponse['Content-Disposition'] = f"attachment; filename=Echeancier_{ inscription.student.lastname }_{ inscription.student.firstname }.pdf"
    return reponse

@unauthenticated_customer
def status_paye_parent(request, student_id):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    # Recuperer la salle
    inscription = Inscription.objects.filter(student_id=student_id, anneeacademique_id=anneeacademique_id).first()
    # Récuperer tous les mois de l'année académique
    months = periode_annee_scolaire(anneeacademique_id)
    date_actuel = date.today() # date actuelle
    month_actuel = date_actuel.strftime("%m") # Mois actuel
    month_actuel = format_month(month_actuel)
    # Récuperer tous les mois du début de la rentrée jusqu'au mois actuel
    tabMonths = []
    for month in months:
        if month == month_actuel:
            tabMonths.append(month)
            break
        else:
            tabMonths.append(month)
            
    # Récuperer tous les paiements de l'étudiant du début de la rentrée jusqu'à ce jour
    tabMonthPaye = []
    montant_restant = 0
    for month in tabMonths:
        dic = {}
        dic["month"] = month
        # Verifier s'il est autoriser à payer ce mois ou pas
        autorisation = AutorisationPayment.objects.filter(salle_id=inscription.salle.id, student_id=student_id, month=month, anneeacademique_id=anneeacademique_id)
        # Verifier si les élèves de cette salles sont autorisés à payer ce mois
        query_autorisation_salle = AutorisationPayment.objects.filter(salle_id=inscription.salle.id, month=month, anneeacademique_id=anneeacademique_id)
        if autorisation.exists() or query_autorisation_salle.exists():
            dic["status"] = "Ne paye pas"
        else:
            payment = Payment.objects.filter(salle_id=inscription.salle.id, student_id=student_id, month=month, anneeacademique_id=anneeacademique_id)
            if payment.exists():
                paye = payment.first()
                if paye.amount < inscription.salle.price:
                    dic["status"] = "Avance"
                    montant_restant += (inscription.salle.price - paye.amount)
                else:
                    dic["status"] = "Payé"
            else:
                dic["status"] = "Impayé"
                montant_restant += inscription.salle.price
                
        tabMonthPaye.append(dic)
        
    context = {
       "setting": setting,
       "months": tabMonthPaye,
       "montant_restant": montant_restant
    }
    return render(request, "status_paye_parent.html", context)

@login_required(login_url='connection/account') 
@allowed_users(allowed_roles=permission_gestionnaire)
def dette_parents(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    parents = Parent.objects.all()
    tabparents = []
    total = 0
    for parent in parents:
        dic_parent = {}
        # Récuperer les enfants du parent
        students = Student.objects.filter(parent_id=parent.id)
        tabstudents = [] # Liste des enfants du parent qui sont inscris cette année
        dette_totale = 0
        for student in students:
            query = Inscription.objects.filter(student_id=student.id, anneeacademique_id=anneeacademique_id)
            if query.exists():
                dic_student = {}
                
                inscription = query.first()
                # Récuperer tous les mois de l'année académique
                months = periode_annee_scolaire(anneeacademique_id)
                date_actuel = date.today() # date actuelle
                month_actuel = date_actuel.strftime("%m") # Mois actuel
                month_actuel = format_month(month_actuel)
                # Récuperer tous les mois du début de la rentrée jusqu'au mois actuel
                tabMonths = []
                for month in months:
                    if month == month_actuel:
                        tabMonths.append(month)
                        break
                    else:
                        tabMonths.append(month)
                        
                # Récuperer tous les paiements de l'étudiant du début de la rentrée jusqu'à ce jour
                montant_restant = 0
                for month in tabMonths:
                    # Verifier s'il est autoriser à payer ce mois ou pas
                    autorisation = AutorisationPayment.objects.filter(salle_id=inscription.salle.id, student_id=inscription.student.id, month=month, anneeacademique_id=anneeacademique_id)
                    # Verifier si les étudiants de cette salle ne sont pas autorisés à payer ce mois
                    query_autorisation = AutorisationPaymentSalle.objects.filter(salle_id=inscription.salle.id, month=month, anneeacademique_id=anneeacademique_id)
                    if autorisation.exists() or query_autorisation.exists():
                        pass
                    else:
                        payment = Payment.objects.filter(salle_id=inscription.salle.id, student_id=inscription.student.id, month=month, anneeacademique_id=anneeacademique_id)
                        if payment.exists():
                            paye = payment.first()
                            if paye.amount < inscription.salle.price:
                                montant_restant += (inscription.salle.price - paye.amount)
                        else:
                            montant_restant += inscription.salle.price
                            
                if montant_restant:
                    dic_student["student"] = student
                    dic_student["dette"] = montant_restant
                    
                    tabstudents.append(dic_student)
                     
                dette_totale += montant_restant
                
        if dette_totale:  
            dic_parent["parent"] = parent
            dic_parent["students"] = tabstudents
            dic_parent["nombre_enfants"] = len(tabstudents)
            dic_parent["dette"] = dette_totale
            
            date_actuel = date.today() # date actuelle
            month_actuel = date_actuel.strftime("%m") # Mois actuel
            month_actuel = format_month(month_actuel)
            if Notification.objects.filter(parent_id=parent.id, month=month_actuel, anneeacademique_id=anneeacademique_id).exists():
                dic_parent["status"] = True
            else:
                dic_parent["status"] = False
                
            tabparents.append(dic_parent)
            
            total += dette_totale 
            
        
    context = {
       "setting": setting,
       "parents": tabparents,
       "total": total
    }
    return render(request, "dette_parents.html", context)

@login_required(login_url='connection/account') 
@allowed_users(allowed_roles=permission_gestionnaire)
def add_notification(request, parent_id, montant):
    
    anneeacademique_id = request.session.get('anneeacademique_id')
    user_id = request.user.id
    date_actuel = date.today() # date actuelle
    month_actuel = date_actuel.strftime("%m") # Mois actuel
    month_actuel = format_month(month_actuel)
    mont = int(montant)
    notif = Notification(parent_id=parent_id, user_id=user_id, amount=mont, month=month_actuel, anneeacademique_id=anneeacademique_id)
    
    # Nombre de notifications avant l'ajout
    count0 = Notification.objects.all().count()
    notif.save()
    # Nombre de notifications après l'ajout
    count1 = Notification.objects.all().count()
    # On verifie si l'insertion a eu lieu ou pas.
    context = {}
    if count0 < count1:
        context = { "status": "success"}
    else:
        context = { "status": "error"}
    return render(request, "add_notification.html", context)

@unauthenticated_customer   
def notification_parent(request):
    anneeacademique_id = request.session.get('anneeacademique_id')
    parent_id = request.session.get('parent_id')
    setting = get_setting(anneeacademique_id)
    if setting is None:
        return redirect("settings/maintenance")
    
    notifications = Notification.objects.filter(parent_id=parent_id, anneeacademique_id=anneeacademique_id)
    for notification in notifications:
        notification.status = True
        notification.save()
        
    context = {
        "setting": setting,
        "notifications": notifications
    }
    return render(request, "notification_parent.html", context)