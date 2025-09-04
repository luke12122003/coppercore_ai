#validating data and storing metadata to geospatial dataset model
import os
import rasterio
import geopandas as gpd
from .models import geospatialDatasets

def file_validation(dataset_upload_path):
    extension = os.path.splitext(dataset_upload_path)[1].lower()

    if extension in ['.tif', '.tiff',]:
        return validate_raster(dataset_upload_path)
    elif extension in ['.shp', '.geojson',]:
        return validate_vector(dataset_upload_path)
    else:
        raise ValueError("file type is not matched")
    

def validate_raster(dataset_upload_path):
    with rasterio.open(dataset_upload_path) as src:
        return{
            "dataset_types": "raster",
            "crs": str(src.crs),
            "band_info": src.count,
            "geometry_types": None
        }


def validate_vector(dataset_upload_path):
    gdf= gpd.read_file(dataset_upload_path)     #GeoDataFrame
    geometry_types = list(gdf.geometry.type.unique())
    return{
        "dataset_types":"vector",
        "crs": str(gdf.crs),
        "band_info": None,
        "geometry_types": ",".join(geometry_types)
    }

# def save_metadata(dataset_upload_path):
#     metadata = file_validation(dataset_upload_path)
#     if metadata:
#         dataset = geospatialDatasets(
#             file_name=os.path.basename(dataset_upload_path),
#             file_type=metadata.get("dataset_types"),
#             crs=metadata.get("crs"),
#             band_count=metadata.get("band_info"),
#             geometry_types=metadata.get("geometry_types"),
#         )
#         dataset.save()
#         return dataset
#     else:
#         raise Exception("validation failed ")

# def save_metadata(dataset_upload_path):
#     # Save to temp
#     with tempfile.NamedTemporaryFile(delete=False, suffix=dataset_upload_path.name) as temp_file:
#         for chunk in dataset_upload_path.chunks():
#             temp_file.write(chunk)
#         temp_path = temp_file.name

#     try:
#         metadata = file_validation(temp_path)
#         if metadata["dataset_types"] != file_type:
#             raise ValueError("Uploaded file content does not match declared file type.")

#         dataset = geospatialDatasetseospatialDataset(
#             file_name=os.path.basename(django_file.name),
#             dataset_types=dataset_types,
#             crs=metadata.get("crs"),
#             band_info=metadata.get("band_info"),
#             geometry_types=metadata.get("geometry_types"),
#         )
#         dataset.save()
#         return dataset