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
    'esri_oceans': {
        'type': 'xyz',
        'title': 'Oceans (Esri)',
        'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
        'attribution': (
            'Tiles © Esri, GEBCO, NOAA, National Geographic, DeLorme, HERE, '
            'Geonames.org, and other contributors'
        ),
    },
    'usgs_imagery': {
        'type': 'xyz',
        'title': 'USGS Imagery',
        'url': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',
        'attribution': 'Tiles courtesy of the U.S. Geological Survey',
    },
    'usgs_imagery_topo': {
        'type': 'xyz',
        'title': 'USGS Imagery Topo',
        'url': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile/{z}/{y}/{x}',
        'attribution': 'Tiles courtesy of the U.S. Geological Survey',
    },
    'eox_sentinel2_cloudless': {
        'type': 'xyz',
        'title': 'Sentinel-2 Cloudless',
        'url': 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg',
        'attribution': (
            'Sentinel-2 cloudless by EOX IT Services GmbH '
            '(contains modified Copernicus Sentinel data 2020)'
        ),
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
