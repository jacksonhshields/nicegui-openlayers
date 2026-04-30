"""Live updates: a marker, a trail, and a moving polygon driven by a timer."""
import math
import time

from nicegui import ui

from nicegui_openlayers import openlayers

m = openlayers(center=(151.21, -33.86), zoom=12, layer_control=True) \
    .style('height: 640px; width: 100%')

m.add_basemap('carto_light')
m.add_basemap('esri_world_imagery', visible=False)

vehicles = m.vector_layer(title='Vehicles', group='Live')
trails = m.vector_layer(title='Trails', group='Live')
zones = m.vector_layer(title='Zones', group='Live')

# A marker that we'll move every 200 ms.
vehicle = vehicles.add_marker((151.21, -33.86), label='Boat 1',
                              popup='<b>Boat 1</b><br>speed: …')

# A trail line that grows over time.
trail = trails.add_line([(151.21, -33.86)], color='#ef4444', width=3)

# A small triangular polygon that will rotate around the centre.
def triangle(lon, lat, theta, size=0.01):
    return [(lon + size * math.cos(theta + i * 2 * math.pi / 3),
             lat + size * math.sin(theta + i * 2 * math.pi / 3)) for i in range(3)]

zone = zones.add_polygon(triangle(151.21, -33.86, 0),
                        fill_color='rgba(34,197,94,0.25)',
                        stroke_color='#16a34a')

t0 = time.time()


def tick():
    t = time.time() - t0
    lon = 151.21 + 0.02 * math.cos(t / 5)
    lat = -33.86 + 0.02 * math.sin(t / 5)
    vehicle.set_position((lon, lat))
    vehicle.set_popup(f'<b>Boat 1</b><br>t={t:.1f}s')
    trail.append_point((lon, lat))
    if len(trail.coords) > 200:
        trail.set_points(trail.coords[-200:])
    zone.set_coords(triangle(lon, lat, t / 3))


ui.timer(0.2, tick)
ui.button('Reset trail', on_click=lambda: trail.set_points([(151.21, -33.86)]))

ui.run()
