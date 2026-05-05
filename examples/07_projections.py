"""Switching map view between EPSG:4326 (WGS84 lon/lat) and UTM zone 56S.

Sydney sits in UTM zone 56S — EPSG:32756 — a metres-based projection that's
common for engineering, surveying and any analysis that wants distances and
areas in real units rather than degrees.

This example shows:

- Registering a custom projection by passing its proj4 definition.
- Switching the live view between EPSG:3857 (the default web-mercator),
  EPSG:4326 (geographic lon/lat), and EPSG:32756 (UTM 56S, metres).
- Drawing in any projection — coordinates round-trip back as lon/lat
  regardless of which projection the view is in.
- Vector features, GeoJSON and the OSM basemap all reproject automatically.

Coordinates that you pass through the Python API are *always* lon/lat
(EPSG:4326). The view projection only affects how the map is rendered and
the units of the cursor coordinate that some user interactions report.
"""
from nicegui import ui

from nicegui_openlayers import openlayers


# proj4 definition strings (also available from https://epsg.io)
UTM56S = ('+proj=utm +zone=56 +south +datum=WGS84 +units=m +no_defs +type=crs')
WGS84 = '+proj=longlat +datum=WGS84 +no_defs +type=crs'

PROJECTIONS = {
    'EPSG:3857': 'Web Mercator (default)',
    'EPSG:4326': 'WGS84 lon/lat (degrees)',
    'EPSG:32756': 'UTM zone 56S (metres)',
}

SYDNEY = (151.2093, -33.8688)


m = openlayers(
    center=SYDNEY,
    zoom=12,
    layer_control=True,
    custom_projections=[
        {'code': 'EPSG:4326', 'proj4': WGS84,
         'extent': [-180, -90, 180, 90]},
        {'code': 'EPSG:32756', 'proj4': UTM56S,
         # UTM 56S valid extent (metres). Centred on 153°E, southern hemisphere.
         'extent': [166021.44, 1116915.04, 833978.56, 10000000.00],
         'worldExtent': [150.0, -80.0, 156.0, 0.0]},
    ],
).style('height: 640px; width: 100%')

m.add_basemap('osm')
m.add_basemap('esri_world_imagery', visible=False)

# A few static vectors — these stay anchored to the same lon/lat regardless
# of which projection the view is in.
landmarks = m.vector_layer(title='Landmarks')
landmarks.add_marker((151.2153, -33.8568), label='Opera House',
                     popup='<b>Sydney Opera House</b>')
landmarks.add_marker((151.2108, -33.8523), label='Harbour Bridge',
                     popup='<b>Sydney Harbour Bridge</b>')
landmarks.add_marker((151.2073, -33.8688), label='Town Hall',
                     popup='<b>Sydney Town Hall</b>')

# A line tracing the harbour bridge approaches
landmarks.add_line(
    [(151.2080, -33.8523), (151.2143, -33.8523), (151.2153, -33.8568)],
    color='#dc2626', width=4,
)

# A polygon outlining the Royal Botanic Garden
landmarks.add_polygon(
    [(151.2148, -33.8650), (151.2235, -33.8650),
     (151.2235, -33.8590), (151.2148, -33.8590),
     (151.2148, -33.8650)],
    fill_color='rgba(34, 197, 94, 0.25)',
    stroke_color='#15803d',
    stroke_width=2,
    popup='<b>Royal Botanic Garden</b>',
)

# A GeoJSON layer to demonstrate that GeoJSON reprojects automatically too.
m.geojson_layer(
    title='Suburbs (sample)',
    data={
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'properties': {'name': '<b>CBD (rough)</b>'},
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [151.198, -33.880], [151.220, -33.880],
                    [151.220, -33.860], [151.198, -33.860],
                    [151.198, -33.880],
                ]],
            },
        }],
    },
    popup_property='name',
    stroke_color='#1e40af',
    fill_color='rgba(30, 64, 175, 0.15)',
    stroke_width=2,
)

# Drawing toolbar — also fully projection-aware.
draw_layer = m.draw_control(types=['Point', 'LineString', 'Polygon', 'Rectangle'])

# Measure tools (distance + angle) and a scale bar. Distance is computed
# geodesically (great-circle), so the answer is independent of the active
# view projection.
m.measure_control(types=['Distance'], units='metric')
m.scale_bar(units='metric')

with ui.row().classes('items-center gap-4'):
    ui.label('View projection:').classes('font-semibold')
    proj_radio = ui.radio(
        list(PROJECTIONS.keys()),
        value='EPSG:3857',
        on_change=lambda e: switch_projection(e.value),
    ).props('inline')
    proj_label = ui.label(PROJECTIONS['EPSG:3857']).classes('text-sm text-gray-500')

with ui.row().classes('items-center gap-4'):
    ui.label('Scale bar units:').classes('font-semibold')
    ui.radio(
        ['metric', 'imperial', 'nautical'],
        value='metric',
        on_change=lambda e: (m.scale_bar(units=e.value),
                             m.measure_control(units=e.value)),
    ).props('inline')
    ui.button('Clear measurements', on_click=m.clear_measurements).props('flat')

cursor_label = ui.label('Click the map to see coordinates.').classes('font-mono text-sm')
draw_log = ui.log(max_lines=12).classes('w-full h-40 font-mono text-xs')


def switch_projection(code: str) -> None:
    m.set_projection(code)
    proj_label.set_text(PROJECTIONS[code])
    draw_log.push(f'view -> {code} ({PROJECTIONS[code]})')


def on_map_click(e):
    lon, lat = e.args['coord']
    cursor_label.set_text(
        f'lon/lat: ({lon:.5f}, {lat:.5f})   ·   view: {m.projection}'
    )


def on_draw(e):
    ftype = e.args['type']
    fid = e.args['feature_id']
    coords = e.args['coords']
    # coords come back in lon/lat regardless of the active view projection
    draw_log.push(f'drew {ftype} {fid} (lon/lat): {coords}')


def on_measure(e):
    kind = e.args['kind']
    text = e.args['text']
    if kind == 'Angle':
        draw_log.push(f'measured angle: {text}')
    else:
        # value is in metres, regardless of the units shown on the map
        draw_log.push(f"measured distance: {text}  ({e.args['value']:.1f} m)")


m.on_map_click(on_map_click)
m.on_draw(on_draw)
m.on_measure(on_measure)
m.on_modify(lambda e: draw_log.push(f"edited {e.args['feature_id']}"))
m.on_delete(lambda e: draw_log.push(f"deleted {e.args['feature_id']}"))

ui.label(
    'All coordinates supplied to nicegui-openlayers are lon/lat (EPSG:4326). '
    'The "view projection" only affects how the map is rendered — switch it to '
    'see the OSM basemap and vectors reproject on the fly. UTM 56S only covers '
    'a 6° strip around eastern Australia, so panning far away from Sydney will '
    'distort or fall outside the projection extent.'
).classes('text-sm text-gray-500')

ui.run()
