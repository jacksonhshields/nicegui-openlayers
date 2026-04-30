# nicegui-openlayers

An [OpenLayers](https://openlayers.org/) map element for [NiceGUI](https://nicegui.io/).

Features:

- Dynamic, live-updating markers, lines, and polygons (move/restyle/append without rebuilding the map)
- Built-in basemaps (OSM, Carto, Esri World Imagery, OpenTopoMap, …) and an exclusive basemap group
- Custom XYZ "slippy" tile layers and **WMS** layers (tiled or single-image)
- **GeoJSON** layers (inline data or remote URL) with live `set_data` / `set_url` / `set_style`
- HTML popups attached to features, plus ad-hoc popups at any coordinate
- SVG icon markers (string-based, easy to template per feature)
- Built-in collapsible **layer-control tree** with checkboxes / radios / opacity sliders
- Interactive **drawing** toolbar: point, line, polygon, rectangle, edit, delete; drawn features round-trip back to Python
- Standard NiceGUI events: `feature_click`, `map_click`, `view_change`, `layer_visibility`, `draw_created`, `draw_modified`, `draw_deleted`
- **Fully offline:** OpenLayers is bundled in the package — no CDN at runtime

All coordinates are `(longitude, latitude)` in EPSG:4326.

## Install

```bash
pip install -e .
```

## Quickstart

```python
from nicegui import ui
from nicegui_openlayers import openlayers

m = openlayers(center=(151.21, -33.86), zoom=12, layer_control=True) \
    .style('height: 600px; width: 100%')

m.add_basemap('osm')
m.add_basemap('esri_world_imagery', visible=False)

boats = m.vector_layer(title='Boats')
boat = boats.add_marker((151.21, -33.86), label='Sydney', popup='<b>Hi!</b>')

# Live-update from anywhere (timer, websocket, asyncio task, ...)
boat.set_position((151.22, -33.87))

ui.run()
```

See `examples/` for:

- `01_basic.py` — the smallest possible map
- `02_live_data.py` — moving marker, growing trail, rotating polygon
- `03_layers.py` — multiple basemaps, a WMS overlay, a custom XYZ overlay, layer tree
- `04_svg_and_popups.py` — SVG markers, popups, click events, live SVG rotation
- `05_drawing.py` — drawing toolbar, edit/delete, drawn features visible from Python
- `06_geojson.py` — load / swap / extend / restyle a GeoJSON layer
- `07_projections.py` — switch the view between EPSG:3857, EPSG:4326 and UTM 56S

## GeoJSON

```python
gj = m.geojson_layer(
    data={                       # or url='/static/buildings.geojson'
        'type': 'FeatureCollection',
        'features': [
            {'type': 'Feature',
             'properties': {'name': '<b>Opera House</b>'},
             'geometry': {'type': 'Point', 'coordinates': [151.2153, -33.8568]}},
        ],
    },
    title='Landmarks',
    popup_property='name',       # property to show as a popup on click
    stroke_color='#dc2626', fill_color='rgba(220,38,38,0.25)',
)

gj.set_data(new_geojson_dict)    # replace all features
gj.set_url('/static/v2.geojson') # switch to a remote URL and reload
gj.refresh()                     # re-fetch the current URL
gj.set_style(stroke_color='#0a0', stroke_width=4, marker_radius=10)
```

Coordinates inside the GeoJSON must be `[lon, lat]` (EPSG:4326). Pass
`data_projection=...` if your data is in a different CRS.

## Drawing

```python
m = openlayers(center=(151.21, -33.86), zoom=13).style('height: 600px')
m.add_basemap('osm')

draw_layer = m.draw_control(types=['Point', 'LineString', 'Polygon', 'Rectangle'])

m.on_draw(lambda e: print('drew', e.args['type'], e.args['coords']))
m.on_modify(lambda e: print('edited', e.args['feature_id']))
m.on_delete(lambda e: print('removed', e.args['feature_id']))

# Programmatic mode switching
m.draw('Polygon')      # arm the polygon tool
m.stop_drawing()       # disarm
m.clear_drawn()        # wipe everything in the draw layer
```

Keyboard while drawing: **Esc** cancels the in-progress sketch, **Backspace/Delete** removes the last vertex.

## Projections

By default the view is rendered in EPSG:3857 (Web Mercator) — the projection
used by OSM and most other web tile layers. To render in a different
projection, register it via proj4 and switch:

```python
m = openlayers(center=(151.21, -33.86), zoom=12, custom_projections=[
    {'code': 'EPSG:32756',
     'proj4': '+proj=utm +zone=56 +south +datum=WGS84 +units=m +no_defs',
     'extent': [166021.44, 1116915.04, 833978.56, 10000000.00],
     'units': 'm'},
])
m.add_basemap('osm')          # OSM tiles get reprojected on the fly
m.set_projection('EPSG:32756')  # render in UTM zone 56S (metres)
```

`define_projection(code, proj4_def, ...)` does the same registration after the
map already exists. All coordinates passed through the Python API are still
`(longitude, latitude)` — only the rendering changes. See
`examples/07_projections.py`.

## Offline use

OpenLayers itself (`ol.js` ~ 820 KB and `ol.css`) is shipped inside the package
under `nicegui_openlayers/frontend/ol/` and served by NiceGUI's static-resource
mechanism. `proj4.js` (~ 90 KB) is bundled the same way under
`nicegui_openlayers/frontend/proj4/` and only loaded on demand when a custom
projection is requested. The page never reaches out to a CDN at runtime, so
the component works in air-gapped or otherwise offline deployments.
