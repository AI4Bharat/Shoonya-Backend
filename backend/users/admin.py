from django.contrib.auth.models import Group
from .models import User
from organizations.models import *
from django.contrib import admin

# Register your models here.

admin.site.register(User)
admin.site.register(Organization)
admin.site.register(Invite)

admin.site.unregister(Group)