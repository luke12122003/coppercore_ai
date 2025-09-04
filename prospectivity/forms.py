
from django import forms
from .models import prospectivityProject, geospatialDatasets
from django.core.exceptions import ValidationError
class ProspectivityProjectForm(forms.ModelForm):
    class Meta:
        model = prospectivityProject
        fields = ['name', 'project_code', 'description', 'project_status', 'country', 'region', 'target_minerals', 'mineral_type']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class GeospatialDatasetForm(forms.ModelForm):
    class Meta:
        model = geospatialDatasets
        fields = ['dataset_names', 'dataset_types', 'file', 'crs', 'band_info']

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['tif', 'tiff', 'zip']:
                raise ValidationError("This file type is not supported")
        return file