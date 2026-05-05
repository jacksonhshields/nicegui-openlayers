"""NiceGUI extension wrapping OpenLayers.

Quickstart::

    from nicegui import ui
    from nicegui_openlayers import openlayers

    m = openlayers(center=(151.21, -33.86), zoom=10, layer_control=True) \\
        .style('height: 600px; width: 100%')

    m.add_basemap('osm')
    m.add_basemap('esri_world_imagery', visible=False)

    boats = m.vector_layer(title='Boats')
    boats.add_marker((151.21, -33.86), label='Sydney', popup='<b>Hello!</b>')

    ui.run()
"""

from .controls import CustomControl
from .features import Feature, Line, Marker, Polygon, SvgMarker
from .layers import GeoJsonLayer, Layer, OsmLayer, VectorLayer, WmsLayer, XyzLayer
from .map import OpenLayersMap, openlayers
from .presets import BASEMAP_PRESETS

__all__ = [
    'BASEMAP_PRESETS',
    'CustomControl',
    'Feature',
    'GeoJsonLayer',
    'Layer',
    'Line',
    'Marker',
    'OpenLayersMap',
    'OsmLayer',
    'Polygon',
    'SvgMarker',
    'VectorLayer',
    'WmsLayer',
    'XyzLayer',
    'openlayers',
]
