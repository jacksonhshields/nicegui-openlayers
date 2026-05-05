"""Custom map controls — buttons rendered on top of the map with Python callbacks.

Mirrors the official OpenLayers example:
    https://openlayers.org/en/latest/examples/custom-controls.html

``map.add_control()`` returns a :class:`CustomControl` whose ``set_html``,
``set_active`` and ``remove`` methods drive the live button. Clicks fire the
Python callable passed as ``on_click``.
"""
from nicegui import ui

from nicegui_openlayers import openlayers

HOME = (151.21, -33.86)  # Sydney
HOME_ZOOM = 12

m = openlayers(center=HOME, zoom=HOME_ZOOM) \
    .style('height: 600px; width: 100%')

m.add_basemap('osm')
m.add_basemap('esri_world_imagery', visible=False)

boats = m.vector_layer(title='Boats')
boats.add_marker(HOME, label='Sydney', popup='<b>Hello, Sydney!</b>')

# 1) A simple home button that resets the view (top-left, under the zoom buttons).
m.add_control(
    html='⌂',
    title='Reset view',
    on_click=lambda: m.set_view(center=HOME, zoom=HOME_ZOOM),
)

# 2) A button whose label updates from Python — it doubles as a click counter.
counter = {'n': 0}

def bump():
    counter['n'] += 1
    count_btn.set_html(f'<b>{counter["n"]}</b>')
    ui.notify(f'Clicked {counter["n"]} time(s)')

count_btn = m.add_control(
    html='<b>0</b>',
    title='Click counter — updates from Python',
    on_click=bump,
)

# 3) A toggle button: stays highlighted while satellite imagery is active.
sat_state = {'on': False}

def toggle_satellite():
    sat_state['on'] = not sat_state['on']
    for layer in m.layers():
        if layer.title == 'Satellite (Esri)':
            layer.set_visible(sat_state['on'])
        elif layer.title == 'OpenStreetMap':
            layer.set_visible(not sat_state['on'])
    sat_btn.set_active(sat_state['on'])

sat_btn = m.add_control(
    html='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
         'stroke-linecap="round" stroke-linejoin="round">'
         '<circle cx="12" cy="12" r="3"/>'
         '<ellipse cx="12" cy="12" rx="10" ry="4"/>'
         '<ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/>'
         '<ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/>'
         '</svg>',
    title='Toggle satellite basemap',
    position='top-right',
    on_click=toggle_satellite,
)

# 4) A button that toggles a companion control on the opposite corner —
#    demonstrates dynamic add/remove of controls from Python.
extra = {'control': None}

def kill_extra():
    if extra['control'] is not None:
        extra['control'].remove()
        extra['control'] = None
        ui.notify('Removed the extra button.')

def toggle_extra():
    if extra['control'] is None:
        extra['control'] = m.add_control(
            html='✕',
            title='I will remove myself when clicked',
            position='bottom-right',
            on_click=kill_extra,
        )
        ui.notify('Added a self-destruct button (bottom-right).')
    else:
        kill_extra()

m.add_control(
    html='+',
    title='Toggle an extra control in the bottom-right',
    position='bottom-left',
    on_click=toggle_extra,
)

ui.label('Custom controls live on top of the map. Try each button — '
         'they are wired to Python callbacks.').classes('text-sm text-gray-600 mt-2')

ui.run()
