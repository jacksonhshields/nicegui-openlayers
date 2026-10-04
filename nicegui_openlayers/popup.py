from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui.element import Element

if TYPE_CHECKING:
    from .map import OpenLayersMap


class Popup(Element):
    """A map popup holding arbitrary NiceGUI content, anchored at a lon/lat.

    Unlike feature ``popup=`` HTML (rendered with ``v-html``, so not
    interactive), anything created inside ``with popup:`` is a live NiceGUI
    element: buttons, inputs, selects and their Python handlers all work.

    The element stays in the map's DOM (the frontend just repositions it on
    every map render), so Vue keeps managing it normally. Clicking empty map
    space or the × button closes it.

    Example::

        pop = m.popup()
        def on_click(e):
            pop.clear()
            with pop:
                ui.label('Boat-1').classes('font-bold')
                ui.button('Stop', on_click=stop_boat)
            pop.open(e.args['feature_coord'] or e.args['coord'])
        m.on_feature_click(on_click)
    """

    def __init__(self, map_: OpenLayersMap, *, classes: str = '', css: dict | None = None) -> None:
        super().__init__('div')
        self._map = map_
        self.coord: tuple[float, float] | None = None
        self._classes.append('nol-element-popup')
        if classes:
            self.classes(classes)
        if css:
            self.style(';'.join(f'{k}:{v}' for k, v in css.items()))
        self.set_visibility(False)
        with self.default_slot:
            close = Element('button')
            close._classes.append('nol-popup-close')
            close._text = '×'
            close.on('click', lambda _: self.close())
            self.content = Element('div')
            self.content._classes.append('nol-element-popup-content')

    # ``with popup:`` and ``clear()`` target the content area, leaving the × button alone.
    def __enter__(self) -> 'Popup':
        self.content.__enter__()
        return self

    def __exit__(self, *_: Any) -> None:
        self.content.__exit__(*_)

    def clear(self) -> 'Popup':
        self.content.clear()
        return self

    @property
    def is_open(self) -> bool:
        return self.coord is not None

    def open(self, coord: tuple[float, float]) -> 'Popup':
        """Show the popup anchored at ``(lon, lat)``."""
        self.coord = (float(coord[0]), float(coord[1]))
        self.set_visibility(True)
        self._map.run_method('open_element_popup', self.id, list(self.coord))
        return self

    def close(self) -> 'Popup':
        if self.coord is None:
            return self
        self.coord = None
        self.set_visibility(False)
        self._map.run_method('close_element_popup', self.id)
        return self
