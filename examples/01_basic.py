"""Smallest possible example: a map with a marker."""
from nicegui import ui

from nicegui_openlayers import openlayers

m = openlayers(center=(151.21, -33.86), zoom=10).style('height: 600px; width: 100%')
m.add_basemap('osm')

boats = m.vector_layer(title='Boats')
boats.add_marker((151.21, -33.86), label='Sydney', popup='<b>Hello, Sydney!</b>')

ui.run()
