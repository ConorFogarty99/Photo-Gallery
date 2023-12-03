from django.db import models

class Photo(models.Model):
    title = models.CharField(max_length=100)
    date_taken = models.DateField()
    film_type = models.CharField(max_length=50)
    camera = models.CharField(max_length=50)
    image = models.ImageField(upload_to='photos/')

    def __str__(self):
        return self.title