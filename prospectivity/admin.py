from django.contrib import admin
from .models import prospectivityProject, geospatialDatasets, MLmodelRun

@admin.register(prospectivityProject)
class prospectivityProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_date', 'project_code')
    search_fields = ('name',)
    ordering = ('-created_date',)

@admin.register(geospatialDatasets)
class geospatialDatasetsAdmin(admin.ModelAdmin):
    list_display = ('dataset_names', 'project', 'dataset_types', 'crs', 'band_info', 'updated_on')
    list_filter = ('dataset_types', 'crs', 'project')
    search_fields = ('dataset_names', 'project__name')  # Fixed: Search on project name
    ordering = ('-updated_on',)

@admin.register(MLmodelRun)
class MLmodelRunAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'project', 'predicted_at')
    list_filter = ('project',)
    search_fields = ('model_name', 'project__name')  # Fixed: Search on project name
    filter_horizontal = ('input_data',)
