from django.db import models
from netbox.models import NetBoxModel
from virtualization.models import VirtualMachine
from dcim.models import Device
from django.urls import reverse

class BusinessApplication(NetBoxModel):
    """
    A model representing a business application in the organization.
    """
    appcode = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.CharField(max_length=100)
    delegate = models.CharField(max_length=100, blank=True, null=True)
    servicenow = models.URLField(blank=True, null=True)
    virtual_machines = models.ManyToManyField(
        VirtualMachine,
        related_name="business_applications",
        blank=True
    )
    devices = models.ManyToManyField(
        Device,
        related_name="business_applications",
        blank=True
    )

    class Meta:
        ordering = ['appcode']

    def get_absolute_url(self):
        """
        Returns the URL to access a detail view of this object.
        """
        return reverse('plugins:business_application:businessapplication_detail', args=[self.pk])

    def __str__(self):
        return self.appcode
