from netbox.plugins import PluginTemplateExtension
from django.db.models import Q

from .models import BusinessApplication
from .tables import BusinessApplicationTable
from virtualization.models import VirtualMachine
from dcim.models import Device

class AppCodeExtension(PluginTemplateExtension):
    def left_page(self):
        if self.context['config'].get('device_ext_page') == 'left':
            return self.x_page()
        return ''

    def right_page(self):
        if self.context['config'].get('device_ext_page', 'right') == 'right':
            return self.x_page()
        return ''

    def full_width_page(self):
        if self.context['config'].get('device_ext_page') == 'full_width':
            return self.x_page()
        return ''

    def _get_related(self, obj):
        return BusinessApplicationTable(BusinessApplication.objects.none())

    def _get_downstream(self, obj):
        return BusinessApplicationTable(BusinessApplication.objects.none())

    def x_page(self):
        obj = self.context['object']
        return self.render(
            'business_application/extend.html',
            extra_context={
                'related_appcodes': self._get_related(obj),
                'downstream_appcodes': self._get_downstream(obj),
            }
        )


class DeviceAppCodeExtension(AppCodeExtension):
    model = 'dcim.device'
    def _get_related(self, obj):
        return BusinessApplicationTable(
            BusinessApplication.objects.filter(devices=obj)
        )

    def _get_downstream(self, obj):
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
                for termination in cable_termination.cable.a_terminations:
                    if termination and termination.device and termination.device.role == node.role and termination.device not in nodes:
                        nodes.append(termination.device)
            current += 1
        return BusinessApplicationTable(apps)

class VMAppCodeExtension(AppCodeExtension):
    model = 'virtualization.virtualmachine'
    def _get_related(self, obj):
        return BusinessApplicationTable(
            BusinessApplication.objects.filter(virtual_machines=obj)
        )

class ClusterAppCodeExtension(AppCodeExtension):
    model = 'virtualization.cluster'
    def right_page(self):
        obj = self.context['object']
        vms = VirtualMachine.objects.filter(cluster=obj)

        # Related App Codes (via VMs)
        related_apps_via_vm = BusinessApplication.objects.filter(virtual_machines__in=vms).distinct()

        # Downstream App Codes (via VMs and their devices)
        downstream_apps = set()
        processed_devices = set()
        for vm in vms:
            downstream_apps.update(BusinessApplication.objects.filter(virtual_machines=vm))
            if vm.host and vm.host not in processed_devices:
                nodes = [vm.host]
                visited_ids = {vm.host.id}
                current = 0
                while current < len(nodes):
                    node = nodes[current]
                    downstream_apps.update(BusinessApplication.objects.filter(Q(devices=node) | Q(virtual_machines__device=node)))
                    for cable_termination in node.cabletermination_set.all():
                        for termination in cable_termination.cable.b_terminations:
                            if hasattr(termination, 'device') and termination.device and termination.device.id not in visited_ids:
                                nodes.append(termination.device)
                                visited_ids.add(termination.device.id)
                        for termination in cable_termination.cable.a_terminations:
                            if hasattr(termination, 'device') and termination.device and termination.device.role == node.role and termination.device.id not in visited_ids:
                                nodes.append(termination.device)
                                visited_ids.add(termination.device.id)
                    current += 1
                processed_devices.add(vm.host)

        return self.render(
            'business_application/cluster_extend.html',  # Render the correct template
            extra_context={
                'related_appcodes': BusinessApplicationTable(related_apps_via_vm),
                'downstream_appcodes': BusinessApplicationTable(list(downstream_apps)),
            }
        )

template_extensions = [
    DeviceAppCodeExtension,
    VMAppCodeExtension,
    ClusterAppCodeExtension,
]
