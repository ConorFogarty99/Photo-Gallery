from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from .models import Photo
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login


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
