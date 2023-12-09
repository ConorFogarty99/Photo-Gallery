from django.db import models

class Photo(models.Model):
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    film_type = models.CharField(max_length=50)
    camera = models.CharField(max_length=50)
    image_url = models.URLField(max_length=1024, default='Null')
    date_taken = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    album = models.CharField(max_length=255, default='Default Album')
    dominant_colors = models.JSONField(default=list)

    def __str__(self):
        return self.title or self.album