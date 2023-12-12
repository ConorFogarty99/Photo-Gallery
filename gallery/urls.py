from django.urls import path, include
from .views import login_view, gallery_view, upload_view, process_album, save_photo_data, delete_photo
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login/', login_view, name='login'),
    path('', gallery_view, name='gallery'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('upload/', upload_view, name='upload_photos'),
    path('process_album/', process_album, name='process_album'),
    path('save-photo-data/', save_photo_data, name='save_photo_data'),
    path('delete-photo/<int:photo_id>/', delete_photo, name='delete_photo'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
