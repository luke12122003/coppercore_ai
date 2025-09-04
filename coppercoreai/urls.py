
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from prospectivity import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.project_view, name='project'),
    path('', include('prospectivity.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
