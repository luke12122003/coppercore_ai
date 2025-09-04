from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from .models import prospectivityProject, geospatialDatasets
from .forms import ProspectivityProjectForm, GeospatialDatasetForm
from django.conf import settings
import zipfile
from pathlib import Path
import os
import shutil
import traceback
import geopandas as gpd
import rasterio
from django.core.files.storage import FileSystemStorage
from datetime import datetime
import matplotlib.pyplot as plt
from .tasks import crsHarmonization, resampleRaster, proximity_to_vector_task
from .model_ML import load_and_generate_predictions
import random
import logging
from django.contrib import messages

# Set up logging
logger = logging.getLogger(__name__)


def upload_view(request):
    datasets = geospatialDatasets.objects.filter(project__isnull=True)
    return render(request, 'prospectivity/dataset_list.html', {'datasets': datasets})

def dataset_upload(request, project_id):
    project = get_object_or_404(prospectivityProject, pk=project_id)
    if request.method == 'POST':
        form = GeospatialDatasetForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.project_id = project_id
            dataset.status = "Validated"
            file = request.FILES['file']
            tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)
            temp_file_path = os.path.join(tmp_dir, file.name)
            print(file.name)
            print("temp file path", temp_file_path)
            with open(temp_file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
                print("file saved")

            try:
                metadata = file_validation(temp_file_path)
                if metadata["dataset_types"].lower() != form.cleaned_data["dataset_types"].lower():
                    return JsonResponse({'error': 'File type does not match actual content'}, status=400)

                dataset.dataset_names = form.cleaned_data["dataset_names"]
                dataset.dataset_types = metadata.get("dataset_types")
                dataset.crs = form.cleaned_data.get("crs")
                dataset.band_info = form.cleaned_data.get("band_info")
                dataset.updated_on = datetime.today().date()
                print("datetime", dataset.updated_on)
                dataset.file.save(file.name, file, save=False)
                dataset.save()
                os.remove(temp_file_path)
                generate_thumbnail(dataset.id)
                datasets = geospatialDatasets.objects.filter(project_id=project_id)
                
                 # Clean up everything in the tmp directory
                tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)

                return render(request, 'prospectivity/partials/upload_form.html', {'datasets': datasets})

            except Exception as e:
                print(traceback.format_exc())
                
                return JsonResponse({'error': str(e)}, status=400)
        else:
            # Return the form with errors
            return render(request, 'prospectivity/partials/dataset_modal_form.html', {
                'form': form,
                'project': project,
                'project_id': project_id,
            }, status=400)

    form = GeospatialDatasetForm()
    datasets = geospatialDatasets.objects.filter(project_id=project_id)
    return render(request, 'prospectivity\project_detail.html', {
        'form': form,
        'datasets': datasets,
        'project': project,
        'project_id': project_id,
    })

def file_validation(dataset_upload_path):
    extension = os.path.splitext(dataset_upload_path)[1].lower()
    if extension in ['.tif', '.tiff']:
        return validate_raster(dataset_upload_path)
    elif extension in ['.zip']:
        return validate_vector_zip(dataset_upload_path)
    else:
        raise ValueError("file type is not matched")

def validate_raster(dataset_upload_path):
    with rasterio.open(dataset_upload_path) as src:
        return {
            "dataset_types": "raster",
            "crs": str(src.crs),
            "band_info": src.count,
            "geometry_types": None
        }

def validate_vector_zip(dataset_upload_path):
    # Use the directory containing the uploaded zip file
    temp_dir = os.path.dirname(dataset_upload_path)
    # Extract zip file to the same directory
    with zipfile.ZipFile(dataset_upload_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Find shapefile (.shp) in extracted files
    shp_file = None
    for file in Path(temp_dir).rglob('*.shp'):
        shp_file = str(file)
        break
    
    if not shp_file:
        raise ValueError("No shapefile found in zip archive")
    
    try:
        # Read and validate shapefile
        gdf = gpd.read_file(shp_file)
        geometry_types = list(gdf.geometry.type.unique())
        
        return {
            "dataset_types": "vector",
            "crs": str(gdf.crs),
            "band_info": None,
            "geometry_types": ",".join(geometry_types)
        }
    finally:
        for file in Path(temp_dir).glob('*.shp') or Path(temp_dir).glob('*.shx') or Path(temp_dir).glob('*.dbf') or Path(temp_dir).glob('*.prj'):
            try:
                os.remove(file)
            except OSError:
                pass

def project_view(request):
    projects = prospectivityProject.objects.all()
    symbols = [
        'symbol1.png',
        'symbol2.png',
        'symbol3.png',
        'symbol4.png',
        'symbol5.png',
        'symbol6.png',
        'symbol7.png'
    ]
    for project in projects:
        project.symbol_image = random.choice(symbols)
    return render(request, 'prospectivity/project.html', {'projects': projects})

def project_create(request):
    if request.method == 'POST':
        form = ProspectivityProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            if request.user.is_authenticated:
                project.user_updated = request.user
            else:
                project.user_updated = None
            project.save()
        projects = prospectivityProject.objects.all()
        symbols = [
        'symbol1.png',
        'symbol2.png',
        'symbol3.png',
        'symbol4.png',
        'symbol5.png',
        'symbol6.png',
        'symbol7.png'
         ]
        for project in projects:
            project.symbol_image = random.choice(symbols)
        return render(request, 'prospectivity/partials/project_form.html', {'projects': projects})
    return redirect('project')

def project_detail(request, project_id):
    project = get_object_or_404(prospectivityProject, pk=project_id)
    datasets = geospatialDatasets.objects.filter(project_id=project.id)
    dataset_form = GeospatialDatasetForm()

    context = {
        'project': project,
        'datasets': datasets,
        'form': dataset_form,
    }
    return render(request, 'prospectivity/project_detail.html', context)

def project_delete(request, project_id):
    project = get_object_or_404(prospectivityProject, id=project_id)
    # Delete related datasets and files
    datasets = geospatialDatasets.objects.filter(project=project)
    for ds in datasets:
        # Delete dataset files
        if ds.file and ds.file.path and os.path.exists(ds.file.path):
            os.remove(ds.file.path)
        # Delete thumbnail if exists
        if ds.thumbnail and ds.thumbnail.path and os.path.exists(ds.thumbnail.path):
            os.remove(ds.thumbnail.path)
        ds.delete()
    # Delete the project folder in media/geospatial_datasets/<project_name>/
    safe_project_name = str(project.name)
    project_folder = os.path.join(settings.MEDIA_ROOT, 'geospatial_datasets', safe_project_name)
    if os.path.isdir(project_folder):
        shutil.rmtree(project_folder)
    # Delete the project itself
    project.delete()
    return redirect('project')

def upload_dataset(request, project_id):
    project = get_object_or_404(prospectivityProject, id=project_id)
    print("running dataset upload")
    if request.method == 'POST':
        form = GeospatialDatasetForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.project = project
            dataset.status = "Validated"
            dataset.save()
            generate_thumbnail(dataset.id)
            datasets = geospatialDatasets.objects.filter(project_id=project_id)
            return render(request, 'prospectivity/partials/upload_form.html', {'datasets': datasets})
    return redirect('project_detail', project_id=project_id)

def dataset_delete(request, dataset_id):
    dataset = get_object_or_404(geospatialDatasets, id=dataset_id)
    project_id = dataset.project.id if dataset.project else None

    # Delete the file from the filesystem
    if dataset.file and dataset.file.path and os.path.exists(dataset.file.path):
        os.remove(dataset.file.path)

    # Delete thumbnail if exists
    if dataset.thumbnail:
        thumb_path = os.path.join(settings.MEDIA_ROOT, str(dataset.thumbnail))
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

    dataset.delete()

    # Redirect back to the project detail page
    if project_id:
        return redirect('project_detail', project_id=project_id)
    return redirect('project')

def trigger_crs(request, dataset_id):
    print(f"Triggering CRS Harmonization for dataset ID: {dataset_id}")
    try:
        dataset = get_object_or_404(geospatialDatasets, id=dataset_id)
        print(f"Dataset found: {dataset.dataset_names}, Current Status: {dataset.status}")
        dataset.status = "Preprocessing"
        dataset.task_message = "Starting CRS Harmonization"
        dataset.save()
        print(f"Dataset status updated to Preprocessing for dataset ID: {dataset_id}")
        if not dataset.project:
            print("No project associated with dataset")
            return JsonResponse({"error": "No project associated with dataset"}, status=400)
        target_crs = dataset.project.target_crs if dataset.project.target_crs else "EPSG:4326"
        print(f"Target CRS: {target_crs}")
        task = crsHarmonization.delay(dataset_id, target_crs)
        print(f"Celery task triggered: {task.id}")
        return JsonResponse({"status": dataset.status, "task_message": dataset.task_message})
    except Exception as e:
        print(f"Error in trigger_crs: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def trigger_resample(request, dataset_id):
    print(f"Triggering Resample for dataset ID: {dataset_id}")
    try:
        dataset = get_object_or_404(geospatialDatasets, id=dataset_id)
        print(f"Dataset found: {dataset.dataset_names}, Current Status: {dataset.status}")

        dataset.status = "Preprocessing"
        dataset.task_message = "Starting raster resampling"
        dataset.save()
        print(f"Dataset status updated to Preprocessing for dataset ID: {dataset_id}")
        print("Dataset type:", dataset.dataset_types)

        # Check project association
        if not dataset.project:
            print("No project associated with dataset")
            return JsonResponse({"error": "No project associated with dataset"}, status=400)

        # Path to constant reference raster
        reference_raster_path = os.path.join(settings.MEDIA_ROOT, 'Const', 'file.tif')
        print(f"Using constant reference raster: {reference_raster_path}")

        # Confirm reference raster file exists
        if os.path.exists(reference_raster_path):
            task = resampleRaster.delay(dataset_id, reference_raster_path)
            print(f"Celery resample task triggered with constant ref: {task.id}")
            return JsonResponse({"status": dataset.status, "task_message": dataset.task_message})
        else:
            print("Reference raster file not found")
            return JsonResponse({"error": "Reference raster not found"}, status=500)
        
        # task = resampleRaster.delay(dataset_id, target_resolution=(30, 30))
    except Exception as e:
        print(f"Error in trigger_resample: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)



def trigger_proximity(request, dataset_id):
    print(f"Triggering Proximity Calculation for dataset ID: {dataset_id}")
    try:
        dataset = get_object_or_404(geospatialDatasets, id=dataset_id)
        print(f"Dataset found: {dataset.dataset_names}, Current Status: {dataset.status}")
        dataset.status = "Preprocessing"
        dataset.task_message = "Starting proximity raster generation"
        dataset.save()
        print(f"Dataset status updated to Preprocessing for dataset ID: {dataset_id}")
        print(dataset.project)
        if not dataset.project:
            print("No project associated with dataset")
            return JsonResponse({"error": "No project associated with dataset"}, status=400)

        # Extract .zip if necessary
        vector_path = dataset.file.path
        if vector_path.endswith('.zip'):
            temp_dir = os.path.join(os.path.dirname(vector_path), f"temp_{dataset_id}")
            os.makedirs(temp_dir, exist_ok=True)
            with zipfile.ZipFile(vector_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            # Find the .shp file in the extracted contents
            for file in os.listdir(temp_dir):
                if file.endswith('.shp'):
                    vector_path = os.path.join(temp_dir, file)
                    break
            if not vector_path.endswith('.shp'):
                shutil.rmtree(temp_dir)
                raise ValueError("No .shp file found in the zip archive")

        task = proximity_to_vector_task.delay(dataset_id, vector_path, temp_dir)
        print(f"Celery proximity task triggered: {task.id}")
        generate_thumbnail(dataset.id)
        return JsonResponse({"status": dataset.status, "task_message": dataset.task_message, "task_id": task.id})

    except Exception as e:
        print(f"Error in trigger_proximity: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)



def status_view(request, dataset_id):
    dataset = get_object_or_404(geospatialDatasets, id=dataset_id)
    return JsonResponse({"status": dataset.status,"task_message": dataset.task_message or ""})

def generate_thumbnail(dataset_id):
    dataset = get_object_or_404(geospatialDatasets, id=dataset_id)
    if dataset.dataset_types == 'raster':
        thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
        os.makedirs(thumbnail_dir, exist_ok=True)  # Create thumbnails directory if it doesn't exist
        thumbnail_path = os.path.join(thumbnail_dir, f'{dataset.id}.png')
        with rasterio.open(dataset.file.path) as src:
            data = src.read(1)
            plt.imsave(thumbnail_path, data, cmap='viridis', vmin=0, vmax=255)
            dataset.thumbnail = f'thumbnails/{dataset.id}.png'
            dataset.save()

def map_view(request):
    return render(request, 'prospectivity/map.html')

def help_view(request):
    return render(request, 'prospectivity/help.html')

def home(request):
    return render(request, 'prospectivity/project.html')



def select_and_predict_datasets(request, project_id):
    project = get_object_or_404(prospectivityProject, id=project_id)
    project_folder = os.path.join(settings.MEDIA_ROOT, 'geospatial_datasets', project.name)
    output_dir = os.path.join(project_folder, 'outputs')
    os.makedirs(output_dir, exist_ok=True)

    if request.method == 'POST':
        selected_model = request.POST.get('model')
        if not selected_model or selected_model.lower() != 'cnn':
            return JsonResponse({'status': 'error', 'message': 'Please select the CNN model.'}, status=400)

        try:
            # Fetch all raster datasets for the project
            selected_datasets = geospatialDatasets.objects.filter(
                project_id=project_id,
                dataset_types='raster'
            )
            if not selected_datasets.exists():
                return JsonResponse({'status': 'error', 'message': 'No raster datasets found for this project.'}, status=400)

            tif_paths = [dataset.file.path for dataset in selected_datasets]
            logger.info(f"Running predictions for files: {tif_paths}")
            load_and_generate_predictions(tif_paths, output_dir)

            heatmap_path = os.path.join(output_dir, 'prediction_map.png')
            csv_path = os.path.join(output_dir, 'predictions.csv')
            world_map_path = os.path.join(output_dir, 'world_map_with_heatmap.html')
            
            heatmap_url = None
            csv_url = None
            world_map_url = None
            
            if os.path.exists(heatmap_path):
                heatmap_url = os.path.join(settings.MEDIA_URL, 'geospatial_datasets', project.name, 'outputs', 'prediction_map.png')
            if os.path.exists(csv_path):
                csv_url = os.path.join(settings.MEDIA_URL, 'geospatial_datasets', project.name, 'outputs', 'predictions.csv')
            if os.path.exists(world_map_path):
                world_map_url = os.path.join(settings.MEDIA_URL, 'geospatial_datasets', project.name, 'outputs', 'world_map_with_heatmap.html')

            return JsonResponse({
                'status': 'success',
                'message': 'Predictions completed successfully!',
                'heatmap_url': heatmap_url,
                'csv_url': csv_url,
                'world_map_url': world_map_url
            })

        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({'status': 'error', 'message': f"Error during prediction: {str(e)}"}, status=500)

    datasets = geospatialDatasets.objects.filter(project_id=project_id)
    heatmap_path = os.path.join(output_dir, 'prediction_map.png')
    csv_path = os.path.join(output_dir, 'predictions.csv')
    world_map_path = os.path.join(output_dir, 'world_map_with_heatmap.html')
    
    heatmap_url = None
    csv_url = None
    world_map_url = None
    
    if os.path.exists(heatmap_path):
        heatmap_url = os.path.join(settings.MEDIA_URL, 'geospatial_datasets', project.name, 'outputs', 'prediction_map.png')
    if os.path.exists(csv_path):
        csv_url = os.path.join(settings.MEDIA_URL, 'geospatial_datasets', project.name, 'outputs', 'predictions.csv')
    if os.path.exists(world_map_path):
        world_map_url = os.path.join(settings.MEDIA_URL, 'geospatial_datasets', project.name, 'outputs', 'world_map_with_heatmap.html')

    context = {
        'project': project,
        'datasets': datasets,
        'heatmap_url': heatmap_url,
        'csv_url': csv_url,
        'world_map_url': world_map_url,
    }
    return render(request, 'prospectivity/project_detail.html', context)

def download_predictions_csv(request, project_id):
    project = get_object_or_404(prospectivityProject, id=project_id)
    csv_path = os.path.join(settings.MEDIA_ROOT, 'geospatial_datasets', 
                           project.name, 'outputs', 'predictions.csv')
    
    if os.path.exists(csv_path):
        return FileResponse(open(csv_path, 'rb'), as_attachment=True, 
                           filename='predictions.csv')
    else:
        messages.error(request, "Predictions CSV file not found.")
        return redirect('select_and_predict_datasets', project_id=project_id)