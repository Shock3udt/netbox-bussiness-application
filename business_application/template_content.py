from netbox.plugins import PluginTemplateExtension
from django.db.models import Q

from .models import BusinessApplication, ServiceDependency
from .tables import BusinessApplicationTable
from virtualization.models import VirtualMachine
from dcim.models import Device

class AppCodeExtension(PluginTemplateExtension):
    # Base class - should NOT have a model attribute
    # Child classes MUST implement their own methods
    pass

class TechnicalServiceAppCodeExtension(AppCodeExtension):
    model = 'business_application.technicalservice'

    def right_page(self):
        obj = self.context['object']
        # Get BusinessApplications related to this TechnicalService
        related_apps = BusinessApplicationTable(
            BusinessApplication.objects.filter(technical_services=obj)
        )

        # Get all business applications affected by services dependent on this one
        dependent_services = ServiceDependency.objects.filter(upstream_service=obj)
        apps = set()
        for dep in dependent_services:
            apps = apps.union(dep.downstream_service.business_apps.all())
        downstream_apps = BusinessApplicationTable(apps)

        return self.render(
            'business_application/businessapplication/device_extend.html',
            extra_context={
                'related_appcodes': related_apps,
                'downstream_appcodes': downstream_apps,
            }
        )

class DeviceAppCodeExtension(AppCodeExtension):
    model = 'dcim.device'

    def right_page(self):
        obj = self.context['object']
        related_apps = BusinessApplicationTable(
            BusinessApplication.objects.filter(devices=obj)
        )

        # Calculate downstream apps
        apps = set()
        nodes = [obj]
        current = 0
        while current < len(nodes):
            node = nodes[current]
            apps = apps.union(BusinessApplication.objects.filter(Q(devices=node) | Q(virtual_machines__device=node)))

            for cable_termination in node.cabletermination_set.all():
                for termination in cable_termination.cable.b_terminations:
                    if termination and termination.device and termination.device not in nodes:
                        nodes.append(termination.device)
            current += 1
        downstream_apps = BusinessApplicationTable(apps)

        return self.render(
            'business_application/businessapplication/device_extend.html',
            extra_context={
                'related_appcodes': related_apps,
                'downstream_appcodes': downstream_apps,
            }
        )

class VMAppCodeExtension(AppCodeExtension):
    model = 'virtualization.virtualmachine'

    def right_page(self):
        obj = self.context['object']
        related_apps = BusinessApplicationTable(
            BusinessApplication.objects.filter(virtual_machines=obj)
        )

        return self.render(
            'business_application/businessapplication/device_extend.html',
            extra_context={
                'related_appcodes': related_apps,
                'downstream_appcodes': BusinessApplicationTable(BusinessApplication.objects.none()),
            }
        )

class ClusterAppCodeExtension(AppCodeExtension):
    model = 'virtualization.cluster'

    def right_page(self):
        obj = self.context['object']

        vms_in_cluster = VirtualMachine.objects.filter(cluster=obj)
        related_apps_via_vm = BusinessApplication.objects.filter(
            virtual_machines__in=vms_in_cluster
        ).distinct()

        return self.render(
            'business_application/businessapplication/cluster_extend.html',
            extra_context={
                'downstream_appcodes': BusinessApplicationTable(list(related_apps_via_vm)),
            }
        )

template_extensions = [
    DeviceAppCodeExtension,
    VMAppCodeExtension,
    ClusterAppCodeExtension,
    TechnicalServiceAppCodeExtension,
]
