import os
import re
import json
import boto3
import random
import traceback
import tempfile
from zipfile import ZipFile
from PIL import Image
from .models import Photo
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required, user_passes_test
from .utils import extract_images_from_zip, cleanup_temp_images, get_dominant_colors, temp_dir
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict
from urllib.parse import urlparse

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')

def is_superuser(user):
    return user.is_superuser

def login_view(request):
    if request.user.is_authenticated:
        return redirect('gallery')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('gallery')
    else:
        form = AuthenticationForm()
    return render(request, 'gallery/login_view.html', {'form': form})

@login_required
def gallery_view(request):
    photos = list(Photo.objects.all())
    random.shuffle(photos)
    return render(request, 'gallery/gallery_view.html', {'photos': photos})

@login_required
@user_passes_test(is_superuser)
def upload_view(request):
    if request.method == 'POST':
        album_zip = request.FILES['album']
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
        filename = fs.save(album_zip.name, album_zip)
        images = extract_images_from_zip(fs.path(filename))
        return JsonResponse({'images': images})
    return render(request, 'gallery/upload_view.html')

def process_album(request):
    if request.method == 'POST':
        album_zip = request.FILES['album']
        images = extract_images_from_zip(album_zip)
        return JsonResponse({'images': images})

@csrf_exempt
def save_photo_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title')
            desc = data.get('description')
            film_type = data.get('film_type')
            camera = data.get('camera')
            date_obj = data.get('date')
            location = data.get('location')
            rotation = data.get('rotation', 0)
            local_image_path = os.path.join(settings.MEDIA_ROOT, data.get('imageUrl'))

            if rotation:
                image = Image.open(local_image_path)
                image = image.rotate(-rotation, expand=True) # Negative rotation for correct direction
                image.save(local_image_path) 

            s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3_image_path = 'albums/' + local_image_path.split('/')[-3] + '/' + local_image_path.split('/')[-1]
            s3_client.upload_file(local_image_path, AWS_STORAGE_BUCKET_NAME, s3_image_path)
            s3_url = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_image_path}'

            dominant_colors = get_dominant_colors(s3_url)

            photo = Photo(title=title, description=desc, film_type=film_type, date_taken=date_obj, location=location, camera=camera, image_url=s3_url, dominant_colors=dominant_colors, album=local_image_path.split('/')[-3])
            photo.save()

            if data.get('is_last_image', False):
                cleanup_temp_images(temp_dir)

            return JsonResponse({'status': 'success'})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def delete_photo(request, photo_id):
    try:
        photo = Photo.objects.get(id=photo_id)
        
        parsed_url = urlparse(photo.image_url)
        bucket_name = AWS_STORAGE_BUCKET_NAME
        key = parsed_url.path.lstrip('/')

        s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        s3.delete_object(Bucket=bucket_name, Key=key)

        photo.delete()

        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@login_required
def albums_view(request):
    photos = Photo.objects.all()
    albums_by_year = defaultdict(set)

    for photo in photos:
        match = re.search(r'(\d{4})', photo.album)
        if match:
            year = match.group(1)
            album_name = photo.album.replace(year, '').strip()  # Remove year and strip whitespace
            albums_by_year[year].add((photo.album, album_name))

    # Convert sets to lists for consistent ordering
    for year in albums_by_year:
        albums_by_year[year] = sorted(albums_by_year[year], key=lambda x: x[1])

    context = {'albums_by_year': dict(albums_by_year)}
    return render(request, 'gallery/albums_view.html', context)

@login_required
def album_photos_view(request, album_name):
    photos = Photo.objects.filter(album=album_name)
    return render(request, 'gallery/album_photos_view.html', {'photos': photos, 'album_name': album_name})

def download_album(request, album_name):
    s3_client = boto3.client('s3')
    photos = Photo.objects.filter(album=album_name)

    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{album_name.replace(" ", "_")}.zip"'

    with ZipFile(response, 'w') as zip_file:
        for photo in photos:
            key = photo.image_url.split('amazonaws.com/')[1]  # Extracting the key from the URL
            print(f"Downloading S3 object with key: {key}")
            with tempfile.NamedTemporaryFile() as temp_file:
                try:
                    s3_client.download_fileobj(settings.AWS_STORAGE_BUCKET_NAME, key, temp_file)
                    temp_file.seek(0)
                    zip_file.write(temp_file.name, os.path.basename(key))
                except Exception as e:
                    print(f"Failed to download file: {e}")

    return response