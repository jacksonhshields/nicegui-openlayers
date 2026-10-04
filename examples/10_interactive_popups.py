"""Interactive popups: live NiceGUI content (buttons, inputs) anchored on the map.

Click a marker to open a popup for it; click empty map space (or ×) to close.
"""
from nicegui import ui

from nicegui_openlayers import openlayers

m = openlayers(center=(151.21, -33.86), zoom=12).style('height: 640px; width: 100%')
m.add_basemap('carto_light')

layer = m.vector_layer(title='Markers')
markers = {}
for name, coord, color in (('Alpha', (151.21, -33.86), '#ef4444'),
                           ('Bravo', (151.24, -33.83), '#10b981')):
    feature = layer.add_marker(coord, label=name, radius=9, fill_color=color)
    markers[feature.id] = {'name': name, 'feature': feature}

pop = m.popup()


def rename(entry, new_name):
    entry['name'] = new_name
    entry['feature'].set_label(new_name)
    ui.notify(f'Renamed to {new_name}')
    pop.close()


def on_feature_click(e):
    entry = markers.get(e.args.get('feature_id'))
    if entry is None:
        return
    pop.clear()
    with pop:
        ui.label(entry['name']).classes('font-bold')
        name_input = ui.input('New name', value=entry['name']).props('dense')
        with ui.row().classes('gap-1'):
            ui.button('Rename', on_click=lambda: rename(entry, name_input.value)).props('size=sm')
            ui.button('Hello', on_click=lambda: ui.notify(f"Hello from {entry['name']}")).props('size=sm flat')
    pop.open(e.args.get('feature_coord') or e.args['coord'])


m.on_feature_click(on_feature_click)

ui.run()
