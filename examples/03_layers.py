"""Multiple basemaps, a WMS overlay, and a custom XYZ slippy layer with the
layer-control panel enabled."""
from nicegui import ui

from nicegui_openlayers import openlayers

m = openlayers(center=(10.0, 50.0), zoom=4, layer_control=True) \
    .style('height: 700px; width: 100%')

# Basemaps belong to an exclusive group: only one is visible at a time.
m.add_basemap('osm')
m.add_basemap('carto_dark', visible=False)
m.add_basemap('opentopomap', visible=False)
m.add_basemap('esri_world_imagery', visible=False)

# A WMS overlay (NASA GIBS — global daily MODIS true-colour).
m.wms_layer(
    url='https://gibs-a.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi',
    layers='MODIS_Terra_CorrectedReflectance_TrueColor',
    title='MODIS true colour',
    params={'VERSION': '1.3.0', 'FORMAT': 'image/png', 'TRANSPARENT': 'true'},
    opacity=0.6,
    visible=False,
    group='Overlays',
)

# A custom XYZ slippy layer (OpenSeaMap seamarks).
m.xyz_layer(
    url='https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
    title='OpenSeaMap seamarks',
    attribution='© OpenSeaMap contributors',
    visible=False,
    group='Overlays',
)

ui.run()
