"""Custom map controls (buttons rendered on top of the OpenLayers viewport).

See :meth:`nicegui_openlayers.OpenLayersMap.add_control` for the user-facing
entry point.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .map import OpenLayersMap

POSITIONS = ('top-left', 'top-right', 'bottom-left', 'bottom-right')


class CustomControl:
    """A button overlaid on the map that fires a Python callback when clicked.

    Created via :meth:`OpenLayersMap.add_control`. The control is rendered as
    a single button inside an OpenLayers control container, so it stacks
    naturally next to the built-in zoom / attribution / scale controls.

    The button content can be plain text, HTML, or inline SVG. Most common
    properties (label, tooltip, active state) can be changed at runtime and
    will sync to the browser.
    """

    def __init__(self,
                 id: str,
                 *,
                 html: str = '',
                 title: str | None = None,
                 position: str = 'top-left',
                 css: dict | None = None,
                 classes: str | None = None,
                 active: bool = False,
                 on_click: Callable[..., Any] | None = None) -> None:
        if position not in POSITIONS:
            raise ValueError(f'position must be one of {POSITIONS}, got {position!r}')
        self.id = id
        self._html = html
        self._title = title
        self._position = position
        self._css = dict(css or {})
        self._classes = classes
        self._active = active
        self._on_click = on_click
        self._map: 'OpenLayersMap | None' = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'html': self._html,
            'title': self._title,
            'position': self._position,
            'css': self._css,
            'classes': self._classes,
            'active': self._active,
        }

    @property
    def html(self) -> str:
        return self._html

    @property
    def title(self) -> str | None:
        return self._title

    @property
    def active(self) -> bool:
        return self._active

    def set_html(self, html: str) -> 'CustomControl':
        """Replace the button content (text, HTML, or inline SVG)."""
        self._html = html
        self._push({'html': html})
        return self

    def set_title(self, title: str | None) -> 'CustomControl':
        """Update the tooltip shown on hover."""
        self._title = title
        self._push({'title': title})
        return self

    def set_active(self, active: bool = True) -> 'CustomControl':
        """Toggle the visual ``active`` state (highlights the button)."""
        self._active = active
        self._push({'active': active})
        return self

    def toggle(self) -> bool:
        """Flip the active state and return the new value."""
        self.set_active(not self._active)
        return self._active

    def on_click(self, handler: Callable[..., Any]) -> 'CustomControl':
        """Attach (or replace) the click handler."""
        self._on_click = handler
        return self

    def remove(self) -> None:
        """Remove the control from the map."""
        if self._map is not None:
            self._map.remove_control(self)

    def _push(self, patch: dict) -> None:
        if self._map is not None and self._map._is_initialized:
            self._map._send_control_update(self.id, patch)
