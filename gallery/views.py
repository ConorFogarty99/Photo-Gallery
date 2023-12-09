import os
import json
import boto3
from dotenv import load_dotenv
from .models import Photo
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .utils import extract_images_from_zip
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from .utils import extract_images_from_zip, cleanup_temp_images
from django.views.decorators.csrf import csrf_exempt
from .utils import get_dominant_colors
from botocore.exceptions import NoCredentialsError
import traceback

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
    photos = Photo.objects.all()
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
        # cleanup_temp_images(temp_dir)
        return JsonResponse({'images': images})

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')

@csrf_exempt
def save_photo_data(request):
    if request.method == 'POST':
        try:
            print("Enter try")
            data = json.loads(request.body)
            title = data.get('title')
            desc = data.get('description')
            film_type = data.get('film_type')
            camera = data.get('camera')
            local_image_path = os.path.join(settings.MEDIA_ROOT, data.get('imageUrl'))

            s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3_image_path = 'albums/' + local_image_path.split('/')[-3] + '/' + local_image_path.split('/')[-1]
            s3_client.upload_file(local_image_path, AWS_STORAGE_BUCKET_NAME, s3_image_path)
            s3_url = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_image_path}'

            dominant_colors = get_dominant_colors(s3_url)

            photo = Photo(title=title, description=desc, film_type=film_type, camera=camera, image_url=s3_url, dominant_colors=dominant_colors, album=local_image_path.split('/')[-3])
            photo.save()

            return JsonResponse({'status': 'success'})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error'}, status=400)