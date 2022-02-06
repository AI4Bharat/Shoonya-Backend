from django.contrib.auth.models import Group
from .models import User
from django.contrib import admin

# Register your models here.

admin.site.register(User)

admin.site.unregister(Group)