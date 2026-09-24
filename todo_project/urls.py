from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    # Sahifalar (Django shablonlari, ma'lumotlar API'dan JS orqali olinadi)
    path('', include('projects.web_urls')),
    path('accounts/', include('accounts.web_urls')),
    path('tasks/', include('tasks.web_urls')),

    path('admin/', admin.site.urls),

    # REST API
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('projects.urls')),
    path('api/', include('tasks.urls')),
    # Swagger'dagi "Log in" tugmasi uchun (xato urinishlar cheklangan)
    path('api-auth/', include('accounts.api_auth_urls')),

    # API hujjatlari
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('docs/', RedirectView.as_view(pattern_name='swagger-ui')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
