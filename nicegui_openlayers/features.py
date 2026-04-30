from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from .layers import VectorLayer


class Feature:
    """Base class for vector features (markers, lines, polygons)."""

    type: str = 'feature'

    def __init__(self, feature_id: str, *, popup: str | None = None) -> None:
        self.id = feature_id
        self.popup = popup
        self._layer: 'VectorLayer | None' = None

    def _spec(self) -> dict:
        return {}

    def to_dict(self) -> dict:
        d = {'id': self.id, 'type': self.type, 'popup': self.popup}
        d.update(self._spec())
        return d

    # ------------------------------------------------------------------
    # mutation helpers
    # ------------------------------------------------------------------

    def _push(self, patch: dict) -> None:
        if self._layer is not None and self._layer._map is not None:
            self._layer._map.run_method(
                'update_feature', self._layer.id, self.id, {**patch, 'type': self.type},
            )

    def set_popup(self, html: str | None) -> 'Feature':
        self.popup = html
        self._push({'popup': html})
        return self

    def remove(self) -> None:
        if self._layer is not None:
            self._layer._remove_feature(self)


# ----------------------------------------------------------------------
# Marker
# ----------------------------------------------------------------------


class Marker(Feature):
    type = 'marker'

    def __init__(self,
                 feature_id: str,
                 *,
                 coords: tuple[float, float],
                 label: str | None = None,
                 popup: str | None = None,
                 icon_url: str | None = None,
                 svg: str | None = None,
                 scale: float = 1.0,
                 anchor: tuple[float, float] = (0.5, 1.0),
                 rotation: float = 0.0,
                 fill_color: str | None = None,
                 stroke_color: str | None = None,
                 stroke_width: float | None = None,
                 radius: float | None = None,
                 extra: dict | None = None) -> None:
        super().__init__(feature_id, popup=popup)
        self.coords = tuple(coords)
        self.label = label
        self.icon_url = icon_url
        self.svg = svg
        self.scale = scale
        self.anchor = tuple(anchor)
        self.rotation = rotation
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.radius = radius
        self.extra = extra or {}

    def _spec(self) -> dict:
        d = {
            'coords': list(self.coords),
            'label': self.label,
            'iconUrl': self.icon_url,
            'svg': self.svg,
            'scale': self.scale,
            'anchor': list(self.anchor),
            'rotation': self.rotation,
            'fillColor': self.fill_color,
            'strokeColor': self.stroke_color,
            'strokeWidth': self.stroke_width,
            'radius': self.radius,
        }
        d.update(self.extra)
        return d

    # live mutators

    def set_position(self, coords: tuple[float, float]) -> 'Marker':
        self.coords = tuple(coords)
        self._push({'coords': list(self.coords)})
        return self

    move_to = set_position

    def set_label(self, label: str | None) -> 'Marker':
        self.label = label
        self._push({'label': label})
        return self

    def set_icon(self, icon_url: str, *, scale: float | None = None) -> 'Marker':
        self.icon_url = icon_url
        self.svg = None
        patch: dict = {'iconUrl': icon_url, 'svg': None}
        if scale is not None:
            self.scale = scale
            patch['scale'] = scale
        self._push(patch)
        return self

    def set_svg(self, svg: str, *, scale: float | None = None,
                anchor: tuple[float, float] | None = None) -> 'Marker':
        self.svg = svg
        self.icon_url = None
        patch: dict = {'svg': svg, 'iconUrl': None}
        if scale is not None:
            self.scale = scale
            patch['scale'] = scale
        if anchor is not None:
            self.anchor = tuple(anchor)
            patch['anchor'] = list(self.anchor)
        self._push(patch)
        return self

    def set_rotation(self, rotation: float) -> 'Marker':
        self.rotation = rotation
        self._push({'rotation': rotation})
        return self

    def set_style(self, **kwargs: Any) -> 'Marker':
        """Update style fields like ``fill_color``, ``stroke_color``, ``radius``..."""
        patch: dict = {}
        mapping = {
            'fill_color': 'fillColor',
            'stroke_color': 'strokeColor',
            'stroke_width': 'strokeWidth',
            'radius': 'radius',
            'scale': 'scale',
            'anchor': 'anchor',
            'rotation': 'rotation',
            'label': 'label',
            'label_color': 'labelColor',
            'label_stroke': 'labelStroke',
            'label_font': 'labelFont',
        }
        for py, js in mapping.items():
            if py in kwargs:
                value = kwargs.pop(py)
                if py == 'anchor' and value is not None:
                    value = list(value)
                if hasattr(self, py):
                    setattr(self, py, value)
                patch[js] = value
        patch.update(kwargs)  # raw passthrough
        self._push(patch)
        return self


class SvgMarker(Marker):
    """Convenience subclass for SVG-icon markers."""

    def __init__(self,
                 feature_id: str,
                 *,
                 coords: tuple[float, float],
                 svg: str,
                 anchor: tuple[float, float] = (0.5, 0.5),
                 scale: float = 1.0,
                 **kwargs: Any) -> None:
        super().__init__(feature_id,
                         coords=coords,
                         svg=svg,
                         anchor=anchor,
                         scale=scale,
                         **kwargs)


# ----------------------------------------------------------------------
# Line
# ----------------------------------------------------------------------


class Line(Feature):
    type = 'line'

    def __init__(self,
                 feature_id: str,
                 *,
                 coords: Sequence[tuple[float, float]],
                 color: str = '#3b82f6',
                 width: float = 3,
                 dash: Sequence[float] | None = None,
                 popup: str | None = None) -> None:
        super().__init__(feature_id, popup=popup)
        self.coords: list[tuple[float, float]] = [tuple(c) for c in coords]
        self.color = color
        self.width = width
        self.dash = list(dash) if dash else None

    def _spec(self) -> dict:
        return {
            'coords': [list(c) for c in self.coords],
            'color': self.color,
            'width': self.width,
            'dash': self.dash,
        }

    def set_points(self, coords: Sequence[tuple[float, float]]) -> 'Line':
        self.coords = [tuple(c) for c in coords]
        self._push({'coords': [list(c) for c in self.coords]})
        return self

    def append_point(self, coord: tuple[float, float]) -> 'Line':
        self.coords.append(tuple(coord))
        self._push({'coords': [list(c) for c in self.coords]})
        return self

    def set_style(self, *,
                  color: str | None = None,
                  width: float | None = None,
                  dash: Sequence[float] | None = None) -> 'Line':
        patch: dict = {}
        if color is not None:
            self.color = color
            patch['color'] = color
        if width is not None:
            self.width = width
            patch['width'] = width
        if dash is not None:
            self.dash = list(dash)
            patch['dash'] = self.dash
        if patch:
            self._push(patch)
        return self


# ----------------------------------------------------------------------
# Polygon
# ----------------------------------------------------------------------


class Polygon(Feature):
    type = 'polygon'

    def __init__(self,
                 feature_id: str,
                 *,
                 coords: Sequence[Sequence[tuple[float, float]]],
                 fill_color: str = 'rgba(59, 130, 246, 0.3)',
                 stroke_color: str = '#1e3a8a',
                 stroke_width: float = 2,
                 dash: Sequence[float] | None = None,
                 popup: str | None = None) -> None:
        super().__init__(feature_id, popup=popup)
        self.coords: list[list[tuple[float, float]]] = [[tuple(c) for c in ring] for ring in coords]
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.dash = list(dash) if dash else None

    def _spec(self) -> dict:
        return {
            'coords': [[list(c) for c in ring] for ring in self.coords],
            'fillColor': self.fill_color,
            'strokeColor': self.stroke_color,
            'strokeWidth': self.stroke_width,
            'dash': self.dash,
        }

    def set_coords(self,
                   coords: Sequence[Sequence[tuple[float, float]]]
                          | Sequence[tuple[float, float]]) -> 'Polygon':
        rings = _normalize_polygon_coords(coords)
        self.coords = [[tuple(c) for c in ring] for ring in rings]
        self._push({'coords': [[list(c) for c in ring] for ring in self.coords]})
        return self

    def set_style(self, *,
                  fill_color: str | None = None,
                  stroke_color: str | None = None,
                  stroke_width: float | None = None,
                  dash: Sequence[float] | None = None) -> 'Polygon':
        patch: dict = {}
        if fill_color is not None:
            self.fill_color = fill_color
            patch['fillColor'] = fill_color
        if stroke_color is not None:
            self.stroke_color = stroke_color
            patch['strokeColor'] = stroke_color
        if stroke_width is not None:
            self.stroke_width = stroke_width
            patch['strokeWidth'] = stroke_width
        if dash is not None:
            self.dash = list(dash)
            patch['dash'] = self.dash
        if patch:
            self._push(patch)
        return self


def _normalize_polygon_coords(coords: Any) -> list[list[tuple[float, float]]]:
    if not coords:
        return []
    first = coords[0]
    if isinstance(first, (list, tuple)) and first and isinstance(first[0], (int, float)):
        return [list(coords)]
    return [list(ring) for ring in coords]
