"""Live panels — overlay reactive NiceGUI content on the map.

Shows two patterns:

1. ``with m.panel(position):`` — context manager that accepts ANY NiceGUI
   element (label, progress, table, chart, even ``ui.html``). Updating the
   data is just NiceGUI: ``label.set_text(...)``, ``progress.set_value(...)``,
   or any of the binding helpers.

2. Multiple panels in different corners cooperate fine. Each call to
   ``panel()`` returns the wrapper element, so the panel's own appearance
   (size, padding, colours) stays under user control via ``.classes()`` /
   ``.style()``.

This example mirrors the platform-dashboard pattern from a Leaflet app:
each platform renders a moving marker plus a corner card showing its live
name, battery, and pose (heading/roll/pitch).
"""
from __future__ import annotations

import math
import random

from nicegui import ui

from nicegui_openlayers import openlayers

m = openlayers(center=(151.21, -33.86), zoom=13).style('height: 600px; width: 100%')
m.add_basemap('osm')

boats = m.vector_layer(title='Platforms')

# ---- platform state -------------------------------------------------------

PLATFORMS = [
    {'key': 'boat-1', 'name': 'Boat-1', 'color': '#2563eb',
     'pos': [151.215, -33.860], 'hdg': 45.0, 'roll': 0.0, 'pitch': 0.0,
     'battery': 78.0, 'status': 'Underway'},
    {'key': 'boat-2', 'name': 'Boat-2', 'color': '#dc2626',
     'pos': [151.205, -33.870], 'hdg': 200.0, 'roll': 0.0, 'pitch': 0.0,
     'battery': 92.0, 'status': 'Survey'},
]

markers = {p['key']: boats.add_marker(tuple(p['pos']),
                                      label=p['name'],
                                      fill_color=p['color'],
                                      stroke_color='#0f172a',
                                      radius=8) for p in PLATFORMS}

# ---- top-left: a small static title banner --------------------------------

with m.panel('top-left',
             css={'top': '0.5em', 'left': '50%', 'transform': 'translateX(-50%)'}) \
        .classes('px-3 py-1 bg-slate-900/80 text-white rounded-full text-sm shadow'):
    ui.label('Live platform telemetry')

# ---- bottom-right: a stacked dashboard with one card per platform ---------

dash_widgets: dict[str, dict[str, object]] = {}

with m.panel('bottom-right').classes(
        'flex flex-col gap-2 bg-transparent') \
        .style('min-width:280px'):
    for p in PLATFORMS:
        with ui.card().classes('w-full p-3 shadow rounded-md bg-white/95'):
            with ui.row().classes('items-center gap-2 w-full'):
                ui.html(f'<span style="display:inline-block;width:14px;height:14px;'
                        f'border-radius:50%;background:{p["color"]}"></span>')
                ui.label(p['name']).classes('text-base font-bold')
                status = ui.label(p['status']).classes('text-xs text-slate-500 ml-auto')

            with ui.row().classes('items-center gap-2 w-full'):
                ui.label('Battery').classes('text-xs w-16')
                bat = ui.linear_progress(value=p['battery'] / 100, show_value=False) \
                    .classes('flex-1')
                bat_pct = ui.label(f'{p["battery"]:.0f}%') \
                    .classes('text-xs w-10 text-right tabular-nums')

            with ui.row().classes('w-full text-xs gap-3 tabular-nums'):
                with ui.column().classes('gap-0'):
                    ui.label('Hdg').classes('text-slate-500')
                    hdg = ui.label(f'{p["hdg"]:.0f}°').classes('font-semibold')
                with ui.column().classes('gap-0'):
                    ui.label('Roll').classes('text-slate-500')
                    roll = ui.label(f'{p["roll"]:+.1f}°').classes('font-semibold')
                with ui.column().classes('gap-0'):
                    ui.label('Pitch').classes('text-slate-500')
                    pitch = ui.label(f'{p["pitch"]:+.1f}°').classes('font-semibold')

        dash_widgets[p['key']] = {
            'status': status,
            'bat': bat, 'bat_pct': bat_pct,
            'hdg': hdg, 'roll': roll, 'pitch': pitch,
        }

# ---- simulated telemetry --------------------------------------------------

def step():
    for p in PLATFORMS:
        p['hdg'] = (p['hdg'] + random.uniform(-6, 6)) % 360
        p['roll'] = max(-25, min(25, p['roll'] + random.uniform(-2, 2)))
        p['pitch'] = max(-15, min(15, p['pitch'] + random.uniform(-1, 1)))
        p['battery'] = max(0, p['battery'] - 0.05)

        # drift north-east-ish along the heading
        rad = math.radians(p['hdg'])
        p['pos'][0] += 0.0001 * math.sin(rad)
        p['pos'][1] += 0.0001 * math.cos(rad)
        markers[p['key']].set_position(tuple(p['pos']))

        w = dash_widgets[p['key']]
        w['hdg'].set_text(f'{p["hdg"]:.0f}°')
        w['roll'].set_text(f'{p["roll"]:+.1f}°')
        w['pitch'].set_text(f'{p["pitch"]:+.1f}°')
        w['bat'].set_value(p['battery'] / 100)
        w['bat_pct'].set_text(f'{p["battery"]:.0f}%')
        if p['battery'] < 25 and w['status'].text != 'Low battery':
            w['status'].set_text('Low battery')
            w['status'].classes(replace='text-xs ml-auto text-red-600 font-semibold')

ui.timer(0.5, step)

ui.label('Telemetry refreshes twice a second; cards update via NiceGUI bindings.') \
    .classes('text-sm text-gray-600 mt-2')

ui.run()
