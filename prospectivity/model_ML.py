import rasterio
import numpy as np
from tensorflow.keras.models import load_model
import tensorflow as tf
import geopandas as gpd
from shapely.geometry import box
import folium
from folium.plugins import HeatMap
import os
import pandas as pd
import logging
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_and_combine_tif_files(tif_paths, patch_size=128):
    logger.info("Loading and combining TIFF files: %s", tif_paths)
    datasets = [rasterio.open(path) for path in tif_paths]
    target_shape = datasets[0].shape
    transform = datasets[0].transform
    crs = datasets[0].crs

    # Verify all datasets have the same shape and CRS
    for ds in datasets[1:]:
        if ds.shape != target_shape:
            raise ValueError(f"All raster datasets must have the same shape. Found {ds.shape} vs {target_shape}")
        if ds.crs != crs:
            raise ValueError(f"All raster datasets must have the same CRS. Found {ds.crs} vs {crs}")

    # Read and stack bands from all datasets
    bands = []
    for ds in datasets:
        data = ds.read()  # Shape: (bands, height, width)
        data = np.transpose(data, [1, 2, 0])  # Shape: (height, width, bands)
        # Take up to 3 bands; if fewer, use the first band repeatedly
        num_bands = data.shape[-1]
        if num_bands >= 3:
            bands.extend([data[:, :, i] for i in range(3)])  
        else:
            for _ in range(3):
                bands.append(data[:, :, 0] if num_bands >= 1 else np.zeros(target_shape))

    # Stack bands to ensure 3 channels
    combined_data = np.stack(bands[:3], axis=-1)  
    logger.info("Combined data shape: %s", combined_data.shape)

    # Normalize the combined data
    combined_data = combined_data.astype('float32')
    normalized_data = np.zeros_like(combined_data)
    for k in range(combined_data.shape[-1]):
        min_val = combined_data[:, :, k].min()
        max_val = combined_data[:, :, k].max()
        if max_val - min_val > 1e-6:
            normalized_data[:, :, k] = (combined_data[:, :, k] - min_val) / (max_val - min_val)
        else:
            normalized_data[:, :, k] = np.zeros_like(combined_data[:, :, k])
    combined_data = normalized_data

    patches = []
    patch_coords = []
    h, w = combined_data.shape[:2]
    for i in range(0, h - patch_size + 1, patch_size):
        for j in range(0, w - patch_size + 1, patch_size):
            patch = combined_data[i:i+patch_size, j:j+patch_size, :]
            if patch.shape == (patch_size, patch_size, 3):  
                patches.append(patch)
                patch_coords.append((i, j))
    patches = np.array(patches)
    logger.info("Patches shape: %s", patches.shape)


    for ds in datasets:
        ds.close()

    return patches, target_shape, patch_coords, patch_size, transform, crs

def reconstruct_prediction_map(predictions, original_shape, patch_coords, patch_size=128):
    logger.info("Reconstructing prediction map with shape: %s", original_shape)
    h, w = original_shape
    prediction_map = np.zeros((h, w), dtype=np.float32)
    for idx, (i, j) in enumerate(patch_coords):
        value = predictions[idx][0]
        prediction_map[i:i+patch_size, j:j+patch_size] = value
    return prediction_map

def load_and_generate_predictions(tif_paths, output_folder):
    logger.info("Starting prediction process with TIFF paths: %s", tif_paths)
    logger.info("TensorFlow version: %s", tf.__version__)
    # Load the CNN model
    model_path = os.path.join(os.path.dirname(__file__), 'model_ai', 'CNN_model.keras')
    logger.info("Loading model from: %s", model_path)
    try:
        model = load_model(model_path, compile=False)
        model.compile(optimizer='adam', loss='binary_crossentropy')
    except ValueError as e:
        logger.warning("Standard loading failed: %s. Trying workaround...", str(e))
        try:
            from tensorflow.keras.layers import InputLayer
            class CustomInputLayer(InputLayer):
                def __init__(self, *args, **kwargs):
                    if 'batch_shape' in kwargs:
                        batch_shape = kwargs.pop('batch_shape')
                        kwargs['shape'] = batch_shape[1:] if batch_shape[0] is None else batch_shape
                    elif 'batch_shape' in kwargs.get('config', {}):
                        batch_shape = kwargs['config'].pop('batch_shape')
                        kwargs['shape'] = batch_shape[1:] if batch_shape[0] is None else batch_shape
                    super().__init__(*args, **kwargs)
            model = load_model(model_path, custom_objects={'InputLayer': CustomInputLayer}, compile=False)
            model.compile(optimizer='adam', loss='binary_crossentropy')
        except Exception as e:
            logger.error("Workaround failed: %s. Trying HDF5 fallback...", str(e))
            try:
                model = load_model(model_path, custom_objects=None, compile=False)
                model.compile(optimizer='adam', loss='binary_crossentropy')
            except Exception as e:
                logger.error("All loading attempts failed: %s", str(e))
                raise RuntimeError(f"Error loading model: %s", str(e))

  
    patches, original_shape, patch_coords, patch_size, transform, crs = load_and_combine_tif_files(tif_paths)

    # Predict
    logger.info("Generating predictions for %d patches with shape %s", len(patches), patches.shape)
    predictions = model.predict(patches, batch_size=16)
    probabilities = predictions
    binary_predictions = (probabilities > 0.95).astype(np.int32)

    # Export probabilities to CSV
    if len(patch_coords) == len(probabilities):
        df = pd.DataFrame({
            'Patch_Top_Left_X_px': [coord[1] for coord in patch_coords],
            'Patch_Top_Left_Y_px': [coord[0] for coord in patch_coords],
            'Probability': probabilities.flatten(),
            'Binary_Prediction': binary_predictions.flatten()
        })
        csv_path = os.path.join(output_folder, 'predictions.csv')
        df.to_csv(csv_path, index=False)
        logger.info("Predictions saved to: %s", csv_path)
    else:
        logger.warning("Number of patch coordinates and predictions do not match. Skipping CSV export.")

    # Reconstruct probability map
    prob_map = reconstruct_prediction_map(probabilities, original_shape, patch_coords, patch_size)

    # Save probability map as .tiff
    with rasterio.open(tif_paths[0]) as src:
        profile = src.profile
        profile.update(dtype=rasterio.float32, count=1, nodata=0.0, transform=transform)
    prob_map_path = os.path.join(output_folder, 'probability_map.tif')
    with rasterio.open(prob_map_path, 'w', **profile) as dst:
        dst.write(prob_map.astype(rasterio.float32), 1)
    logger.info("Probability map saved to: %s", prob_map_path)

    # Generate and save heatmap as PNG
    plt.figure(figsize=(10, 8))
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'custom', [(0, 'darkgreen'), (0.4, 'green'), (0.65, 'yellow'), (1, 'red')]
    )
    plt.imshow(prob_map, cmap=cmap, vmin=0, vmax=1)
    plt.colorbar(label='Probability')
    plt.title('Prediction Heatmap')
    plt.axis('off')
    heatmap_path = os.path.join(output_folder, 'prediction_map.png')
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info("Heatmap saved to: %s", heatmap_path)

    # Generate world map with heatmap
    geometries = []
    prob_values = []
    for (i, j), prob in zip(patch_coords, probabilities):
        x_min, y_max = transform * (j, i)
        x_max, y_min = transform * (j + patch_size, i + patch_size)
        geometries.append(box(x_min, y_min, x_max, y_max))
        prob_values.append(prob[0])

    gdf = gpd.GeoDataFrame({'probability': prob_values, 'geometry': geometries}, crs=crs)
    if crs != 'EPSG:4326':
        gdf = gdf.to_crs(epsg=4326)

    map_center = [gdf.unary_union.centroid.y, gdf.unary_union.centroid.x]
    m = folium.Map(location=map_center, zoom_start=5)

    bounds = [[gdf.geometry.bounds.miny.min(), gdf.geometry.bounds.minx.min()],
              [gdf.geometry.bounds.maxy.max(), gdf.geometry.bounds.maxx.max()]]
    folium.Rectangle(bounds=bounds, color='blue', fill=True, fill_opacity=0.2).add_to(m)

    heat_data = [[point.y, point.x, prob] for point, prob in zip(gdf.geometry.centroid, gdf['probability'])]
    HeatMap(heat_data, radius=int(patch_size / 8.0), gradient={0.4: 'green', 0.65: 'yellow', 1: 'red'}).add_to(m)

    combined_map_path = os.path.join(output_folder, 'world_map_with_heatmap.html')
    m.save(combined_map_path)
    logger.info("Heatmap saved to: %s", combined_map_path)

    return None