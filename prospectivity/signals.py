from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import geospatialDatasets
from .tasks import crsHarmonization, resampleRaster, calculateProximity

@receiver(post_save, sender=geospatialDatasets)
def process_geospatial_dataset(sender, instance, created, **kwargs):
    if created:
        # Trigger CRS Harmonization, Resampling, and Proximity Calculation tasks
        crsHarmonization.delay(instance.id)
        if instance.dataset_types.lower() == 'raster':
            resampleRaster.delay(instance.id)
        elif instance.dataset_types.lower() == 'vector':
            calculateProximity.delay(instance.id)