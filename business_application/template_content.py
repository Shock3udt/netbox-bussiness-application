from netbox.plugins import PluginTemplateExtension

from .models import BusinessApplication
from .tables import BusinessApplicationTable

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
            apps = apps.union(BusinessApplication.objects.filter(devices=node))
            for cable_termination in node.cabletermination_set.all():
                for termination in cable_termination.cable.b_terminations:
                    if termination and termination.device and termination.device not in nodes:
                        nodes.append(termination.device)
                for termination in cable_termination.cable.a_terminations:
                    if termination and termination.device and termination.device.role == termination.device.role and termination.device not in nodes:
                        nodes.append(termination.device)
            current += 1
        return BusinessApplicationTable(apps)

class VMAppCodeExtension(AppCodeExtension):
    model = 'virtualization.virtualmachine'
    def _get_related(self, obj):
        return BusinessApplicationTable(
            BusinessApplication.objects.filter(virtual_machines=obj)
        )

template_extensions = [
    DeviceAppCodeExtension,
    VMAppCodeExtension
]