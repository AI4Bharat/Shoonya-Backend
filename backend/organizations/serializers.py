from rest_framework import serializers

from .models import *

class OrganizationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Organization
        fields = ['title', 'email_domain_name', 'created_by']