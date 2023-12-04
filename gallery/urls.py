from django.urls import path, include
from .views import login_view, gallery_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', login_view, name='login'),
    path('', gallery_view, name='gallery'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
