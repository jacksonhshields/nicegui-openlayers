"""GeoJSON layers — inline data, swap datasets, append features, live restyle.

Demonstrates:

- Loading inline GeoJSON via ``m.geojson_layer(data=...)``
- Replacing the whole document with ``layer.set_data(...)``
- Appending features by mutating the dict and calling ``set_data`` again
- Live styling via ``layer.set_style(stroke_color=..., fill_color=...)``
- ``popup_property`` to wire feature properties to click popups

Coordinates in GeoJSON are ``[lon, lat]`` (EPSG:4326), same as everywhere else
in nicegui-openlayers.
"""
import copy
import random

from nicegui import ui

from nicegui_openlayers import openlayers


SYDNEY = {
    'type': 'FeatureCollection',
    'features': [
        {
            'type': 'Feature',
            'properties': {'name': '<b>Sydney Opera House</b>'},
            'geometry': {'type': 'Point', 'coordinates': [151.2153, -33.8568]},
        },
        {
            'type': 'Feature',
            'properties': {'name': '<b>Sydney Harbour Bridge</b>'},
            'geometry': {
                'type': 'LineString',
                'coordinates': [[151.2080, -33.8523], [151.2143, -33.8523]],
            },
        },
        {
            'type': 'Feature',
            'properties': {'name': '<b>Royal Botanic Garden</b>'},
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [151.2148, -33.8650], [151.2235, -33.8650],
                    [151.2235, -33.8590], [151.2148, -33.8590],
                    [151.2148, -33.8650],
                ]],
            },
        },
    ],
}


MELBOURNE = {
    'type': 'FeatureCollection',
    'features': [
        {
            'type': 'Feature',
            'properties': {'name': '<b>Flinders Street Station</b>'},
            'geometry': {'type': 'Point', 'coordinates': [144.9670, -37.8183]},
        },
        {
            'type': 'Feature',
            'properties': {'name': '<b>Yarra River (sample)</b>'},
            'geometry': {
                'type': 'LineString',
                'coordinates': [
                    [144.9530, -37.8200], [144.9650, -37.8190],
                    [144.9750, -37.8210], [144.9850, -37.8190],
                ],
            },
        },
        {
            'type': 'Feature',
            'properties': {'name': '<b>MCG (rough outline)</b>'},
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [144.9810, -37.8210], [144.9860, -37.8210],
                    [144.9860, -37.8175], [144.9810, -37.8175],
                    [144.9810, -37.8210],
                ]],
            },
        },
    ],
}


CITY_VIEWS = {
    'Sydney':    {'center': (151.215, -33.860), 'zoom': 14, 'data': SYDNEY},
    'Melbourne': {'center': (144.972, -37.819), 'zoom': 14, 'data': MELBOURNE},
}


m = openlayers(center=(151.215, -33.860), zoom=14, layer_control=True) \
    .style('height: 640px; width: 100%')

m.add_basemap('osm')
m.add_basemap('esri_world_imagery', visible=False)

gj = m.geojson_layer(
    data=copy.deepcopy(SYDNEY),
    title='Landmarks',
    popup_property='name',
    stroke_color='#dc2626',
    stroke_width=3,
    fill_color='rgba(220, 38, 38, 0.25)',
    marker_radius=8,
)

status = ui.label('Loaded: Sydney')


def load_city(name: str) -> None:
    cfg = CITY_VIEWS[name]
    gj.set_data(copy.deepcopy(cfg['data']))
    m.set_view(cfg['center'], cfg['zoom'])
    status.set_text(f'Loaded: {name}')


def add_random_point() -> None:
    """Append a fresh feature to the *current* GeoJSON and re-push it."""
    name = status.text.split(': ', 1)[-1]
    cfg = CITY_VIEWS.get(name, CITY_VIEWS['Sydney'])
    cx, cy = cfg['center']
    # current data lives on the layer — mutate a copy and push it back
    doc = copy.deepcopy(gj.data) if gj.data else {'type': 'FeatureCollection', 'features': []}
    lon = cx + random.uniform(-0.01, 0.01)
    lat = cy + random.uniform(-0.01, 0.01)
    doc['features'].append({
        'type': 'Feature',
        'properties': {'name': f'<b>Random</b><br>({lon:.4f}, {lat:.4f})'},
        'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
    })
    gj.set_data(doc)
    status.set_text(f'Loaded: {name} (+{len(doc["features"])} features)')


def random_style() -> None:
    def hex_colour() -> str:
        return '#%02x%02x%02x' % (random.randint(0, 255),
                                   random.randint(0, 255),
                                   random.randint(0, 255))
    stroke = hex_colour()
    fill_rgb = tuple(random.randint(60, 230) for _ in range(3))
    gj.set_style(
        stroke_color=stroke,
        stroke_width=random.choice([2, 3, 4]),
        fill_color=f'rgba({fill_rgb[0]}, {fill_rgb[1]}, {fill_rgb[2]}, 0.25)',
        marker_radius=random.choice([5, 7, 9, 11]),
    )


def clear_all() -> None:
    gj.set_data({'type': 'FeatureCollection', 'features': []})
    status.set_text('Loaded: (empty)')


with ui.row():
    ui.button('Load Sydney',    on_click=lambda: load_city('Sydney'))
    ui.button('Load Melbourne', on_click=lambda: load_city('Melbourne'))
    ui.button('Add point',      on_click=add_random_point).props('outline')
    ui.button('Random style',   on_click=random_style).props('outline')
    ui.button('Clear',          on_click=clear_all).props('flat color=negative')

ui.label('Click a feature to see its "name" property as a popup.').classes('text-sm text-gray-500')

ui.run()
