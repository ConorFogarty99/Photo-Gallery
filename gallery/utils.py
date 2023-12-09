from colorthief import ColorThief
from PIL import Image
import requests
from io import BytesIO
import os
import zipfile
import shutil
from django.conf import settings

temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_images')

def get_dominant_colors(image_url, num_colors=5):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    img.save('temp_image.png') 
    color_thief = ColorThief('temp_image.png')
    dominant_colors = color_thief.get_palette(color_count=num_colors, quality=1)
    print(dominant_colors)
    return dominant_colors

def extract_images_from_zip(zip_file):
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_images')
    os.makedirs(temp_dir, exist_ok=True)
    image_paths = []

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for file in zip_ref.namelist():
            if not file.startswith('__MACOSX/') and file.lower().endswith(('.jpg', '.jpeg')):
                zip_ref.extract(file, temp_dir)
                relative_path = os.path.join('temp_images', file)
                image_paths.append(relative_path)
    return image_paths

def cleanup_temp_images(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
