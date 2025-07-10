from django.contrib import admin
from django.urls import path, include
from school.views import index
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path("", index, name="index"),
    path('admin/', admin.site.urls),
    path('school/', include("school.urls")),
    path('anneeacademique/', include("anneeacademique.urls")),
    path('auth/', include("app_auth.urls")),
    path('matiere/', include("matiere.urls")),
    path('classe/', include("classe.urls")),
    path('serie/', include("serie.urls")),
    path('salle/', include("salle.urls")),
    path('inscription/', include("inscription.urls")),
    path('programme/', include("programme.urls")),
    path('enseignement/', include("enseignement.urls")),
    path('composition/', include("composition.urls")),
    path('emploitemps/', include("emploi_temps.urls")),
    path('absence/', include("absence.urls")),
    path('publication/', include("publication.urls")),
    path('activity/', include("activity.urls")),
    path('paiement/', include("paiement.urls")),
    path('contact/', include("contact.urls")),
    path('emargement/', include("emargement.urls")),
    path('cours/', include("cours.urls")),
    path('renumeration/', include("renumeration.urls")),
    path('calendrier/', include("calendrier.urls")),
    path('depense/', include("depense.urls")),
    path('cycle/', include("cycle.urls")),
    path('etablissement/', include("etablissement.urls"))
]

#if settings.DEBUG:
urlpatterns +=static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
