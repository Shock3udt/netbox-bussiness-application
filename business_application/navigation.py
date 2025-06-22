from django.conf import settings
from netbox.plugins import PluginMenuItem, PluginMenu, PluginMenuButton
from netbox.choices import ButtonColorChoices


_business_menu_items = (
    PluginMenuItem(
        link='plugins:business_application:businessapplication_list',
        link_text='Business Applications',
    ),
    PluginMenuItem(
        link='plugins:business_application:technicalservice_list',
        link_text='Technical Services',
    ),
)

_operations_menu_items = (
    PluginMenuItem(
        link='plugins:business_application:event_list',
        link_text='Events',
    ),
    PluginMenuItem(
        link='plugins:business_application:eventsource_list',
        link_text='Event Sources',
    ),
    PluginMenuItem(
        link='plugins:business_application:maintenance_list',
        link_text='Maintenance',
    ),
)

_change_menu_items = (
    PluginMenuItem(
        link='plugins:business_application:change_list',
        link_text='Changes',
    ),
    PluginMenuItem(
        link='plugins:business_application:changetype_list',
        link_text='Change Types',
    ),
)

_calendar_menu_items = (
    PluginMenuItem(
        link='plugins:business_application:calendar_view',
        link_text='Calendar',
        buttons=(
            PluginMenuButton(
                link='plugins:business_application:calendar_view',
                title='View Calendar',
                icon_class='mdi mdi-calendar',
                color=ButtonColorChoices.BLUE
            ),
        )
    ),
)


menu = PluginMenu(
    label="Business Application",
    groups=(
        ("Business", _business_menu_items),
        ("Operations", _operations_menu_items),
        ("Change Management", _change_menu_items),
        ("Calendar", _calendar_menu_items),
    ),
    icon_class="mdi mdi-apps",
)
