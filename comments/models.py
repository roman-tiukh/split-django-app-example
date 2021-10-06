from django.db import models

# Create your models here.


class Comment(models.Model):
    post = models.ForeignKey('first.Post', models.PROTECT)
    message = models.CharField(max_length=180)
