# copercore-ai/urls.py

from django.urls import path
from . import  views 
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('dataset/upload/', views.upload_dataset, name='upload_dataset'),
    path('dataset/delete/<int:dataset_id>/', views.dataset_delete, name='dataset_delete'),
    path('project/', views.project_view, name='project'),
    path('project/create/', views.project_create, name='project_create'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('project/<int:project_id>/dataset/upload/', views.dataset_upload, name='dataset_upload'),
    path('project/delete/<int:project_id>/', views.project_delete, name='project_delete'),
    path('map/', views.map_view, name='map'),
    path('help/', views.help_view, name='help'),

    path('trigger_crs/<int:dataset_id>/', views.trigger_crs, name='trigger_crs'),
    path('trigger_resample/<int:dataset_id>/', views.trigger_resample, name='trigger_resample'),
    path('trigger_proximity/<int:dataset_id>/', views.trigger_proximity, name='trigger_proximity'),
    path('status/<int:dataset_id>/', views.status_view, name='status_view'),
    path('select-datasets/<int:project_id>/', views.select_and_predict_datasets, 
         name='select_and_predict_datasets'),
    path('download-csv/<int:project_id>/', views.download_predictions_csv, 
         name='download_predictions_csv'),
 ] #+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)