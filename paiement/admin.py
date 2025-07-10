from django.contrib import admin

from .models import Payment, AutorisationPayment, AutorisationPaymentSalle, Notification, PaymentEtablissement, AutorisationPaymentEtablissement, ContratEtablissement

admin.site.register(Payment)
admin.site.register(AutorisationPayment)
admin.site.register(AutorisationPaymentSalle)
admin.site.register(Notification)
admin.site.register(ContratEtablissement)
admin.site.register(AutorisationPaymentEtablissement)
admin.site.register(PaymentEtablissement)
