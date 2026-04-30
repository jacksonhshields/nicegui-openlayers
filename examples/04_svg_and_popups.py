"""SVG markers, click-driven popups, and a custom popup at an arbitrary point."""
from nicegui import ui

from nicegui_openlayers import openlayers


def boat_svg(color: str = '#ef4444', heading: float = 0) -> str:
    return f'''
    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="-18 -18 36 36">
      <g transform="rotate({heading})">
        <path d="M0,-14 L10,12 L0,7 L-10,12 Z"
              fill="{color}" stroke="#1e293b" stroke-width="1.5" stroke-linejoin="round"/>
        <circle r="2" fill="#1e293b"/>
      </g>
    </svg>'''


m = openlayers(center=(151.21, -33.86), zoom=12, layer_control=True) \
    .style('height: 640px; width: 100%')

m.add_basemap('carto_light')
m.add_basemap('esri_world_imagery', visible=False)

fleet = m.vector_layer(title='Fleet')

red = fleet.add_svg_marker((151.21, -33.86), boat_svg('#ef4444'),
                           anchor=(0.5, 0.5),
                           popup='<b>Red boat</b><br>This popup is HTML.')

green = fleet.add_svg_marker((151.24, -33.83), boat_svg('#10b981', heading=30),
                             anchor=(0.5, 0.5),
                             popup='<b>Green boat</b>')

# A circle marker with a label
fleet.add_marker((151.18, -33.88), label='HQ', radius=8,
                 fill_color='#f59e0b', stroke_color='#78350f',
                 popup='<b>Headquarters</b>')


# Show a popup at an arbitrary coordinate when a button is clicked.
ui.button('Pop somewhere',
          on_click=lambda: m.open_popup((151.20, -33.90),
                                        '<b>Custom popup</b><br>Anywhere on the map.'))


# React to feature clicks (in addition to the auto-popup).
def show_click(e):
    ui.notify(f"Clicked feature {e.args.get('feature_id')} on layer {e.args.get('layer_id')}")


m.on_feature_click(show_click)
m.on_map_click(lambda e: ui.notify(f"Map @ {e.args.get('coord')}"))

# Rotate the red boat with a slider, in real time.
ui.slider(min=0, max=360, value=0,
          on_change=lambda e: red.set_svg(boat_svg('#ef4444', heading=e.value),
                                          anchor=(0.5, 0.5))) \
    .props('label-always').classes('w-96')

ui.run()
