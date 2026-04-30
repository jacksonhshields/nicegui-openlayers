"""Interactive drawing: place points/lines/polygons/rectangles, edit, delete.

Drawn features stay accessible from Python — every shape that comes back through
``on_draw`` ends up in ``draw_layer.features()``. This example shows two ways to
read the coordinates: directly from the event payload, and via the typed
``Marker`` / ``Line`` / ``Polygon`` objects in the layer.
"""
from nicegui import ui

from nicegui_openlayers import Line, Marker, Polygon, openlayers

m = openlayers(center=(151.21, -33.86), zoom=13, layer_control=True) \
    .style('height: 640px; width: 100%')

m.add_basemap('osm')
m.add_basemap('esri_world_imagery', visible=False)

draw_layer = m.draw_control(
    types=['Point', 'LineString', 'Polygon', 'Rectangle'],
    modify=True,
    snap=True,
    continuous=False,
    title='Drawn',
)

count_label = ui.label('No shapes yet.')
coord_log = ui.log(max_lines=20).classes('w-full h-48 font-mono text-xs')


def refresh_count():
    count_label.set_text(f'{len(draw_layer.features())} shape(s) drawn')


def fmt(coord):
    """Format a (lon, lat) tuple to a short string."""
    return f'({coord[0]:.5f}, {coord[1]:.5f})'


def on_draw(e):
    # Option A: read coordinates straight from the event payload.
    #   - 'marker'  → [lon, lat]
    #   - 'line'    → [[lon, lat], ...]
    #   - 'polygon' → [[[lon, lat], ...], ...]   (outer ring first, then holes)
    ftype = e.args['type']
    fid = e.args['feature_id']
    coords = e.args['coords']
    coord_log.push(f'created {ftype} {fid}: {coords}')
    ui.notify(f'Drew {ftype} → {fid}')
    refresh_count()


def on_modify(e):
    # ``coords`` in the modify event already reflects the new shape.
    coord_log.push(f"edited  {e.args['feature_id']}: {e.args['coords']}")


def dump_features():
    """Option B: walk the layer and inspect typed feature objects."""
    feats = draw_layer.features()
    if not feats:
        coord_log.push('--- no features ---')
        return
    coord_log.push(f'--- {len(feats)} feature(s) ---')
    for f in feats:
        if isinstance(f, Marker):
            coord_log.push(f'  marker  {f.id} @ {fmt(f.coords)}')
        elif isinstance(f, Line):
            pts = ', '.join(fmt(c) for c in f.coords)
            coord_log.push(f'  line    {f.id} ({len(f.coords)} pts): {pts}')
        elif isinstance(f, Polygon):
            ring = f.coords[0]  # outer ring
            coord_log.push(f'  polygon {f.id} ({len(ring)} verts on outer ring)')
            for c in ring:
                coord_log.push(f'      {fmt(c)}')


m.on_draw(on_draw)
m.on_modify(on_modify)
m.on_delete(lambda e: (
    coord_log.push(f"deleted {e.args['feature_id']}"),
    ui.notify(f"Deleted {e.args['feature_id']}"),
    refresh_count(),
))

with ui.row():
    ui.button('Draw point',     on_click=lambda: m.draw('Point'))
    ui.button('Draw line',      on_click=lambda: m.draw('LineString'))
    ui.button('Draw polygon',   on_click=lambda: m.draw('Polygon'))
    ui.button('Draw rectangle', on_click=lambda: m.draw('Rectangle'))
    ui.button('Stop',           on_click=m.stop_drawing).props('flat')
    ui.button('Clear all',      on_click=m.clear_drawn).props('flat color=negative')
    ui.button('Print coords',   on_click=dump_features).props('outline')

ui.run()
