from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    pass


class Post(models.Model):
    title = models.CharField(max_length=100)
    body = models.TextField()

