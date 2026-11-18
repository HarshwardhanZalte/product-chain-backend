from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    ROLES = [
        ('farmer', 'FARMER'),
        ('collector', 'COLLECTOR'),
        ('lab', 'LAB'),
        ('factory', 'FACTORY'),
        ('admin', 'ADMIN'),
    ]
    
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    
    role = models.CharField(max_length=20, choices=ROLES, default='farmer')