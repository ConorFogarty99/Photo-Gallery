from django.urls import path, include
from .views import login_view, gallery_view, upload_view, process_album, save_photo_data, delete_photo, albums_view, album_photos_view, download_album
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
    path('albums/', albums_view, name='albums'),
    path('albums/<str:album_name>/', album_photos_view, name='album_photos'),
    path('download-album/<str:album_name>/', download_album, name='download_album'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
