import os
import json
import boto3
import random
import traceback
from PIL import Image
from .models import Photo
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required, user_passes_test
from .utils import extract_images_from_zip, cleanup_temp_images, get_dominant_colors, temp_dir
from django.views.decorators.csrf import csrf_exempt

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

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')

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