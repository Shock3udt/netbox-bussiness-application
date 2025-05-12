from rest_framework import serializers
from business_application.models import BusinessApplication
from dcim.models import Device

class BusinessApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the BusinessApplication model.
    Provides representation for API interactions.
    """
    devices = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Device.objects.all()
    )
    
    class Meta:
        model = BusinessApplication
        fields = [
            'id',
            'name',
            'appcode',
            'description',
            'owner',
            'delegate',
            'servicenow',
            'virtual_machines',  # Assumes virtual_machines is a ManyToMany field
            'devices',
        ]
        extra_kwargs = {
            'virtual_machines': {'read_only': True},
            'devices': {'read_only': True},
        }

class BusinessApplicationSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessApplication
         fields = [
            'id',
            'name',
            'appcode',
            'owner',
            'delegate',
            'servicenow',
        ]

class DeviceWithApplicationsSerializer(serializers.ModelSerializer):
    business_applications = BusinessApplicationSlimSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Device
        fields = [
            'id',
            'name',
            'region',
            'site',
            'device_type',
            'serial_number',
            'business_applications',
        ]
