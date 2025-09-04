#https://medium.com/django-unleashed/asynchronous-tasks-in-django-a-step-by-step-guide-to-celery-and-docker-integration-b6f9898b66b5

from celery import shared_task
from .models import MLmodelRun
from .models import geospatialDatasets
import rasterio
import os
from rasterio import features
from pyproj import Proj, transform
import fiona 
from rasterio.enums import Resampling
import geopandas as gpd 
from scipy.ndimage import distance_transform_edt
from rasterio.warp import calculate_default_transform, reproject, Resampling
from django.conf import settings
from django.db import transaction
import shutil
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
import numpy as np
import time

@shared_task
def MLmodelRunTask(modelRunId):
    try:
        modelRun = MLmodelRun.objects.get(id = modelRunId)
        modelRunStatus = "Running"
        modelRun.save()

        #load dataset
        #prepare features
        #split the data
        #train the model
        #evaluate model

        #update model run status
        modelRunStatus = "Completed"
        modelRunAccuracy = "Accuracy"
        modelRun.modelPath = "modelPath"
        modelRun.save()
    
    except Exception as e:
        modelRunStatus = "Failed"
        modelRun.error_message = str(e)
        modelRun.save()
        raise 


#crs harmonisation
#https://docs.qgis.org/3.40/en/docs/gentle_gis_introduction/coordinate_reference_systems.html

TARGET_CRS = "EPSG:4326"
@shared_task
def crsHarmonization(dataset_id, target_crs="EPSG:4326"):
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    
    # Construct absolute paths for PROJ_LIB and GDAL_DATA
    proj_lib_path = os.path.join(project_dir, 'coppercoreai', 'venv39', 'Lib', 'site-packages', 'rasterio', 'proj_data')
    gdal_data_path = os.path.join(project_dir, 'coppercoreai', 'venv39', 'Lib', 'site-packages', 'rasterio', 'gdal_data')
    
    # Set environment variables
    os.environ['PROJ_LIB'] = proj_lib_path
    os.environ['GDAL_DATA'] = gdal_data_path
    print(f"PROJ_LIB set to: {os.environ['PROJ_LIB']}")
    print(f"GDAL_DATA set to: {os.environ['GDAL_DATA']}")
    print(f"Starting CRS Harmonization for dataset ID: {dataset_id}, Target CRS: {target_crs}")
    
    try:
        dataset = geospatialDatasets.objects.get(id=dataset_id)
        print(f"Dataset found: {dataset.dataset_names}, Type: {dataset.dataset_types}")
        
        input_path = dataset.file.path
        print(f"Input file path: {input_path}")
        
        if dataset.dataset_types.lower() == "vector":
            gdf = gpd.read_file(input_path)
            print(f"Original CRS: {gdf.crs}")
            gdf = gdf.to_crs(target_crs)
            print(f"Reprojected to CRS: {gdf.crs}")
            # Create temporary reprojected file
            temp_path = input_path.replace(".shp", "_reprojected.shp")
            gdf.to_file(temp_path, driver='GeoJSON')
            print(f"Created temporary reprojected vector: {temp_path}")
            
            # Delete the original file and associated files
            if os.path.exists(input_path):
                os.remove(input_path)
                print(f"Deleted original file: {input_path}")
                # Remove associated vector files (.shx, .dbf, etc.)
                base_name = os.path.splitext(input_path)[0]
                for ext in ['.shx', '.dbf', '.prj', '.cpg']:
                    assoc_file = f"{base_name}{ext}"
                    if os.path.exists(assoc_file):
                        os.remove(assoc_file)
                        print(f"Deleted associated file: {assoc_file}")
            
            # Rename the temporary file to the original name
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    os.replace(temp_path, input_path)
                    print(f"Renamed reprojected file to original name: {input_path}")
                    break
                except PermissionError as e:
                    if attempt == max_retries - 1:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        raise e
                    print(f"Permission error on attempt {attempt + 1}, retrying after delay: {str(e)}")
                    time.sleep(1)
            
            dataset.status = "Ready"
            base_name = os.path.splitext(input_path)[0]
            relative_path = input_path.split('geospatial_datasets\\')[-1]
            dataset.task_message = f"Reprojected vector renamed to geospatial_datasets\\{relative_path}"
            
        elif dataset.dataset_types.lower() == "raster":
            # Read the raster data
            src = rasterio.open(input_path)
            print(f"Original CRS: {src.crs}")
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            profile = src.profile
            profile.update({
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            
            # Create temporary reprojected file
            temp_path = input_path.replace(".tif", "_reprojected.tif")
            with rasterio.open(temp_path, 'w', **profile) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=rasterio.enums.Resampling.nearest
                    )
            # Explicitly close the source file
            src.close()
            print(f"Created temporary reprojected raster: {temp_path}")
            
            # Delete the original file
            if os.path.exists(input_path):
                os.remove(input_path)
                print(f"Deleted original file: {input_path}")
            
            # Rename the temporary file to the original name
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    os.replace(temp_path, input_path)
                    print(f"Renamed reprojected file to original name: {input_path}")
                    break
                except PermissionError as e:
                    if attempt == max_retries - 1:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        raise e
                    print(f"Permission error on attempt {attempt + 1}, retrying after delay: {str(e)}")
                    time.sleep(1)
            
            dataset.status = "Ready"
            relative_path = input_path.split('geospatial_datasets\\')[-1]
            dataset.task_message = f"Reprojected vector renamed to geospatial_datasets\\{relative_path}"
        
        else:
            raise ValueError("Unsupported dataset type")
        
        dataset.save()
        print(f"Dataset updated: Status={dataset.status}, Message={dataset.task_message}")
        return dataset.task_message
    except Exception as e:
        print(f"Error in crsHarmonization: {str(e)}")
        dataset.status = "Failed"
        dataset.task_message = f"CRS Harmonization failed: {str(e)}"
        dataset.save()
        return str(e)

#https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/resample.htm


#resampling
@shared_task
def resampleRaster(dataset_id, reference_raster):
    try:
        dataset = geospatialDatasets.objects.get(id=dataset_id)
        print(f"Dataset found: {dataset.dataset_names}, Type: {dataset.dataset_types}")
        input_raster = dataset.file.path
        print(f"Input file path: {input_raster}")
    except Exception as e:
        print(f"Error fetching dataset in resampleRaster: {str(e)}")
        dataset.status = "Failed"
        dataset.task_message = f"Resampling failed: {str(e)}"
        dataset.save()
        return str(e)

    print(f"Starting resampling for input_raster: {input_raster}, reference_raster: {reference_raster}")
    try:
        # Get pixel size from reference raster
        with rasterio.open(reference_raster) as ref:
            ref_transform = ref.transform
            ref_crs = ref.crs
            ref_pixel_size_x = abs(ref_transform.a)
            ref_pixel_size_y = abs(ref_transform.e)
            print(f"Reference raster CRS: {ref_crs}, Pixel size: ({ref_pixel_size_x}, {ref_pixel_size_y})")

            if ref_pixel_size_x == 0 or ref_pixel_size_y == 0:
                raise ValueError("Reference raster has invalid pixel size (0).")

        with rasterio.open(input_raster) as src:
            src_crs = src.crs
            src_bounds = src.bounds
            src_width = src.width
            src_height = src.height
            print(f"Input bounds: {src_bounds}, CRS: {src_crs}, Shape: ({src_height}, {src_width})")

            # Check CRS compatibility
            if src_crs != ref_crs:
                print(f"Warning: Input CRS ({src_crs}) differs from reference CRS ({ref_crs}). Proceeding with input CRS.")

            # Calculate original extent
            extent_width = src_bounds.right - src_bounds.left
            extent_height = src_bounds.top - src_bounds.bottom
            print(f"Input extent: Width={extent_width}, Height={extent_height}")

            # Preserve original aspect ratio (width / height)
            original_aspect_ratio = src_width / src_height
            print(f"Original aspect ratio: {original_aspect_ratio}")

            # Calculate new dimensions based on reference pixel size, preserving aspect ratio
            # Use the smaller pixel size (x or y) to determine the base scale
            target_pixel_size = min(ref_pixel_size_x, ref_pixel_size_y)
            if target_pixel_size >= extent_width or target_pixel_size >= extent_height:
                raise ValueError("Reference pixel size is too large for the input extent.")

            # Calculate new height based on extent and target pixel size, then adjust width
            new_height = round(extent_height / target_pixel_size)
            new_width = round(new_height * original_aspect_ratio)
            print(f"Calculated dimensions: (height={new_height}, width={new_width})")

            # Validate dimensions
            if new_width <= 0 or new_height <= 0:
                raise ValueError(f"Calculated dimensions ({new_height}, {new_width}) are invalid (<= 0). Check pixel size and bounds.")
            if new_width > 100000 or new_height > 100000:
                raise ValueError(f"Calculated dimensions ({new_height}, {new_width}) are too large. Check pixel size.")

            # Calculate new pixel size to preserve original bounds
            new_pixel_size_x = extent_width / new_width
            new_pixel_size_y = extent_height / new_height
            print(f"New pixel size: (x={new_pixel_size_x}, y={new_pixel_size_y})")

            # Build new transform using original bounds and new pixel size
            new_transform = rasterio.transform.from_origin(
                src_bounds.left, src_bounds.top,
                new_pixel_size_x, new_pixel_size_y
            )

            # Resample
            data = src.read(
                out_shape=(src.count, new_height, new_width),
                resampling=Resampling.bilinear
            )

            profile = src.profile.copy()
            profile.update({
                'transform': new_transform,
                'width': new_width,
                'height': new_height,
                'crs': src_crs,
            })
            print(f"Resampled data shape: {data.shape}")

        # Save to temp
        temp_path = input_raster.replace(".tif", "_resampled.tif")
        with rasterio.open(temp_path, 'w', **profile) as dst:
            dst.write(data)
        print(f"Created temporary resampled raster: {temp_path}")

        # Replace original
        if os.path.exists(input_raster):
            os.remove(input_raster)
            print(f"Deleted original file: {input_raster}")

        for attempt in range(5):
            try:
                os.replace(temp_path, input_raster)
                print(f"Renamed resampled file to original name: {input_raster}")
                break
            except PermissionError as e:
                if attempt == 4:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise e
                print(f"Permission error on attempt {attempt + 1}, retrying...")
                time.sleep(1)

        dataset.status = "Ready"
        relative_path = input_raster.split('geospatial_datasets\\')[-1]
        dataset.task_message = f"Resampled raster to: {relative_path}"
        dataset.save()
        print(f"Dataset updated: Status={dataset.status}, Message={dataset.task_message}")

        return dataset.task_message

    except Exception as e:
        error_message = f"Error in resampleRaster: {str(e)}"
        print(error_message)
        dataset.status = "Failed"
        dataset.task_message = error_message
        dataset.save()
        return error_message


#proximity
@shared_task
def proximity_to_vector_task(vector_id, vector_path, temp_dir=None):
    print(f"Starting proximity task for vector_id: {vector_id}")
    try:
        # Fetch vector dataset
        with transaction.atomic():
            vector = geospatialDatasets.objects.select_for_update().get(id=vector_id)
            project = vector.project  # Assuming project is a related field

        print(f"Vector path: {vector_path}")

        # Read vector data
        gdf = gpd.read_file(vector_path)
        print(f"Vector CRS: {gdf.crs}")

        # Calculate raster extent from vector bounds
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        extent_width = bounds[2] - bounds[0]
        extent_height = bounds[3] - bounds[1]
        print(f"Vector bounds: {bounds}, Extent: Width={extent_width}, Height={extent_height}")

        # Define raster resolution (adjustable, default to ~100m at equator for EPSG:4326)
        pixel_size = 0.0009  # Approx. 100m, configurable as needed
        width = int(np.ceil(extent_width / pixel_size))
        height = int(np.ceil(extent_height / pixel_size))
        print(f"Calculated raster dimensions: (height={height}, width={width})")

        # Validate dimensions
        if width <= 0 or height <= 0:
            raise ValueError(f"Calculated dimensions ({height}, {width}) are invalid (<= 0). Check pixel size and bounds.")
        if width > 100000 or height > 100000:
            raise ValueError(f"Calculated dimensions ({height}, {width}) are too large. Check pixel size.")

        # Create transform
        transform = rasterio.transform.from_origin(bounds[0], bounds[3], pixel_size, -pixel_size)

        # Rasterize vector to binary raster
        shapes = [(geom, 1) for geom in gdf.geometry if geom is not None and not geom.is_empty]
        if not shapes:
            raise ValueError("No valid geometries found in vector file")
        binary_raster = rasterize(
            shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype='uint8'
        )
        print(f"Binary raster created with shape: {binary_raster.shape}")

        # Calculate distance transform
        distance = distance_transform_edt(binary_raster == 0) * pixel_size
        print(f"Distance transform calculated with shape: {distance.shape}")

        # Create temporary proximity raster
        temp_path = vector_path.replace(".shp", "_proximity.tif")
        meta = {
            'driver': 'GTiff',
            'height': height,
            'width': width,
            'count': 1,
            'dtype': 'float32',
            'crs': gdf.crs.to_string() if gdf.crs else 'EPSG:4326',  # Default to WGS84 if CRS is None
            'transform': transform,
            'nodata': None
        }
        with rasterio.open(temp_path, 'w', **meta) as dst:
            dst.write(distance.astype(np.float32), 1)
        print(f"Created temporary proximity raster: {temp_path}")

        # Determine project folder path dynamically
        project_folder = os.path.join(settings.MEDIA_ROOT, "geospatial_datasets", project.name)
        os.makedirs(project_folder, exist_ok=True)
        
        # Derive final path from dataset.file.path, adjusting for project folder and .tif extension
        base_filename = os.path.basename(vector.file.path).replace(".zip", "_proximity.tif")
        final_path = os.path.join(project_folder, base_filename)

        # Move the proximity raster to the project folder
        max_retries = 5
        for attempt in range(max_retries):
            try:
                os.replace(temp_path, final_path)
                print(f"Moved proximity raster to project folder: {final_path}")
                break
            except PermissionError as e:
                if attempt == max_retries - 1:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise e
                print(f"Permission error on attempt {attempt + 1}, retrying after delay: {str(e)}")
                time.sleep(1)

        # Delete the original .zip file
        original_zip_path = vector.file.path
        if os.path.exists(original_zip_path) and original_zip_path.endswith('.zip'):
            os.remove(original_zip_path)
            print(f"Deleted original zip file: {original_zip_path}")

        # Update dataset
        with transaction.atomic():
            vector = geospatialDatasets.objects.select_for_update().get(id=vector_id)
            # Update file reference to the new location relative to MEDIA_ROOT
            vector.file.name = os.path.relpath(final_path, settings.MEDIA_ROOT).replace("\\", "/")
            vector.dataset_types = "raster"
            vector.status = "Ready"
            vector.task_message = f"Proximity raster generated: {final_path}"
            vector.save()
            print(f"Dataset updated: Status={vector.status}, Message={vector.task_message}")

        # Clean up temporary directory if used
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")

        return vector.task_message
    except Exception as e:
        error_message = f"Error in proximity_to_vector_task: {str(e)}"
        print(error_message)
        with transaction.atomic():
            vector = geospatialDatasets.objects.select_for_update().get(id=vector_id)
            vector.status = "Failed"
            vector.task_message = error_message
            vector.save()
        return error_message