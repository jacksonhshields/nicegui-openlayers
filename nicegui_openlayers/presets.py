"""Built-in basemap presets that can be added with ``map.add_basemap('osm')``."""

BASEMAP_PRESETS = {
    'osm': {
        'type': 'osm',
        'title': 'OpenStreetMap',
    },
    'osm_hot': {
        'type': 'xyz',
        'title': 'OSM Humanitarian',
        'url': 'https://{a-c}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
        'attribution': '© OpenStreetMap contributors, Tiles courtesy of HOT',
    },
    'carto_light': {
        'type': 'xyz',
        'title': 'Carto Light',
        'url': 'https://{a-d}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        'attribution': '© CARTO © OpenStreetMap contributors',
    },
    'carto_dark': {
        'type': 'xyz',
        'title': 'Carto Dark',
        'url': 'https://{a-d}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'attribution': '© CARTO © OpenStreetMap contributors',
    },
    'esri_world_imagery': {
        'type': 'xyz',
        'title': 'Satellite (Esri)',
        'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        'attribution': 'Tiles © Esri',
    },
    'opentopomap': {
        'type': 'xyz',
        'title': 'OpenTopoMap',
        'url': 'https://{a-c}.tile.opentopomap.org/{z}/{x}/{y}.png',
        'attribution': '© OpenTopoMap (CC-BY-SA)',
    },
    'stamen_toner': {
        'type': 'xyz',
        'title': 'Stamen Toner',
        'url': 'https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}.png',
        'attribution': '© Stadia Maps © Stamen Design © OpenStreetMap contributors',
    },
    'stamen_terrain': {
        'type': 'xyz',
        'title': 'Stamen Terrain',
        'url': 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png',
        'attribution': '© Stadia Maps © Stamen Design © OpenStreetMap contributors',
    },
}
