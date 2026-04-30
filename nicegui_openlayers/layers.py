from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any, Sequence

from .features import Feature, Line, Marker, Polygon, SvgMarker

if TYPE_CHECKING:
    from .map import OpenLayersMap

_feature_id_counter = itertools.count()


def _new_feature_id() -> str:
    return f'feat-{next(_feature_id_counter)}'


class Layer:
    """Base class for OpenLayers layers.

    Layers are owned by an :class:`OpenLayersMap`. After being created, all
    mutating methods proxy to the client through ``run_method`` calls.
    """

    type: str = 'layer'

    def __init__(self,
                 layer_id: str,
                 *,
                 title: str | None = None,
                 group: str | None = None,
                 visible: bool = True,
                 opacity: float = 1.0,
                 z_index: int | None = None,
                 exclusive: bool = False,
                 basemap: bool = False,
                 source_options: dict | None = None) -> None:
        self.id = layer_id
        self.title = title or layer_id
        self.group = group
        self.visible = visible
        self.opacity = opacity
        self.z_index = z_index
        self.exclusive = exclusive
        self.basemap = basemap
        self.source_options = source_options or {}
        self._map: 'OpenLayersMap | None' = None

    # to be overridden
    def _spec(self) -> dict:
        return {}

    def to_dict(self) -> dict:
        d = {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'group': self.group,
            'visible': self.visible,
            'opacity': self.opacity,
            'exclusive': self.exclusive,
            'basemap': self.basemap,
            'sourceOptions': self.source_options,
        }
        if self.z_index is not None:
            d['zIndex'] = self.z_index
        d.update(self._spec())
        return d

    def features(self) -> list[Feature]:  # noqa: D401  -- iterable accessor
        return []

    # ------------------------------------------------------------------
    # public mutators (live)
    # ------------------------------------------------------------------

    def set_visible(self, visible: bool) -> 'Layer':
        self.visible = visible
        if self._map is not None:
            self._map.run_method('set_layer_visible', self.id, visible)
        return self

    def set_opacity(self, opacity: float) -> 'Layer':
        self.opacity = opacity
        if self._map is not None:
            self._map.run_method('set_layer_opacity', self.id, opacity)
        return self

    def set_z_index(self, z_index: int) -> 'Layer':
        self.z_index = z_index
        if self._map is not None:
            self._map.run_method('set_layer_z_index', self.id, z_index)
        return self

    def update_source(self, *, url: str | None = None, params: dict | None = None) -> 'Layer':
        """Update the underlying tile/WMS source (e.g. swap the URL or WMS params)."""
        payload: dict = {}
        if url is not None:
            payload['url'] = url
        if params is not None:
            payload['params'] = params
        if self._map is not None and payload:
            self._map.run_method('set_layer_source_options', self.id, payload)
        return self

    def remove(self) -> None:
        if self._map is not None:
            self._map.remove_layer(self)


class OsmLayer(Layer):
    type = 'osm'


class XyzLayer(Layer):
    """Slippy-map / XYZ tile layer (e.g. ``https://.../{z}/{x}/{y}.png``)."""

    type = 'xyz'

    def __init__(self,
                 layer_id: str,
                 *,
                 url: str,
                 attribution: str | None = None,
                 cross_origin: str | None = None,
                 **kwargs: Any) -> None:
        super().__init__(layer_id, **kwargs)
        self.url = url
        self.attribution = attribution
        self.cross_origin = cross_origin

    def _spec(self) -> dict:
        return {
            'url': self.url,
            'attribution': self.attribution,
            'crossOrigin': self.cross_origin,
        }


class WmsLayer(Layer):
    """WMS layer (tiled by default; pass ``tiled=False`` for single-image WMS)."""

    type = 'wms'

    def __init__(self,
                 layer_id: str,
                 *,
                 url: str,
                 params: dict,
                 tiled: bool = True,
                 server_type: str | None = None,
                 cross_origin: str | None = None,
                 **kwargs: Any) -> None:
        super().__init__(layer_id, **kwargs)
        self.url = url
        self.params = params
        self.tiled = tiled
        self.server_type = server_type
        self.cross_origin = cross_origin

    def _spec(self) -> dict:
        return {
            'url': self.url,
            'params': self.params,
            'tiled': self.tiled,
            'serverType': self.server_type,
            'crossOrigin': self.cross_origin,
        }

    def update_params(self, params: dict) -> 'WmsLayer':
        """Merge new WMS parameters and push to the client (e.g. change the time slice)."""
        self.params.update(params)
        if self._map is not None:
            self._map.run_method('set_layer_source_options', self.id, {'params': self.params})
        return self


class GeoJsonLayer(Layer):
    """Vector layer fed from a GeoJSON document.

    Supply either inline ``data`` (a Python dict in GeoJSON shape) or a remote
    ``url`` for the client to fetch. Coordinates are assumed to be in
    EPSG:4326 unless ``data_projection`` says otherwise.
    """

    type = 'geojson'

    def __init__(self,
                 layer_id: str,
                 *,
                 data: dict | None = None,
                 url: str | None = None,
                 stroke_color: str = '#1e3a8a',
                 stroke_width: float = 2,
                 fill_color: str = 'rgba(59, 130, 246, 0.3)',
                 marker_radius: float = 6,
                 dash: Sequence[float] | None = None,
                 popup_property: str | None = None,
                 data_projection: str = 'EPSG:4326',
                 **kwargs: Any) -> None:
        super().__init__(layer_id, **kwargs)
        self.data = data
        self.url = url
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.fill_color = fill_color
        self.marker_radius = marker_radius
        self.dash = list(dash) if dash else None
        self.popup_property = popup_property
        self.data_projection = data_projection

    def _spec(self) -> dict:
        return {
            'data': self.data,
            'url': self.url,
            'strokeColor': self.stroke_color,
            'strokeWidth': self.stroke_width,
            'fillColor': self.fill_color,
            'markerRadius': self.marker_radius,
            'dash': self.dash,
            'popupProperty': self.popup_property,
            'dataProjection': self.data_projection,
        }

    def set_data(self, data: dict) -> 'GeoJsonLayer':
        """Replace the layer's features with a new inline GeoJSON document."""
        self.data = data
        self.url = None
        if self._map is not None:
            self._map.run_method('update_geojson', self.id,
                                 {'data': data, 'url': None})
        return self

    def set_url(self, url: str) -> 'GeoJsonLayer':
        """Switch to fetching from ``url`` and reload."""
        self.url = url
        self.data = None
        if self._map is not None:
            self._map.run_method('update_geojson', self.id,
                                 {'url': url, 'data': None})
        return self

    def refresh(self) -> 'GeoJsonLayer':
        """Re-fetch the current ``url`` (no-op for inline data)."""
        if self._map is not None and self.url:
            self._map.run_method('update_geojson', self.id, {'url': self.url})
        return self

    def set_style(self, *,
                  stroke_color: str | None = None,
                  stroke_width: float | None = None,
                  fill_color: str | None = None,
                  marker_radius: float | None = None,
                  dash: Sequence[float] | None = None) -> 'GeoJsonLayer':
        patch: dict = {}
        if stroke_color is not None:
            self.stroke_color = stroke_color
            patch['strokeColor'] = stroke_color
        if stroke_width is not None:
            self.stroke_width = stroke_width
            patch['strokeWidth'] = stroke_width
        if fill_color is not None:
            self.fill_color = fill_color
            patch['fillColor'] = fill_color
        if marker_radius is not None:
            self.marker_radius = marker_radius
            patch['markerRadius'] = marker_radius
        if dash is not None:
            self.dash = list(dash)
            patch['dash'] = self.dash
        if patch and self._map is not None:
            self._map.run_method('update_geojson', self.id, patch)
        return self


class VectorLayer(Layer):
    """Vector layer that holds markers, lines, and polygons."""

    type = 'vector'

    def __init__(self, layer_id: str, **kwargs: Any) -> None:
        super().__init__(layer_id, **kwargs)
        self._features: list[Feature] = []

    def features(self) -> list[Feature]:
        return list(self._features)

    # ------------------------------------------------------------------
    # feature factories
    # ------------------------------------------------------------------

    def add_marker(self,
                   coords: tuple[float, float],
                   *,
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
                   **style: Any) -> Marker:
        m = Marker(_new_feature_id(),
                   coords=coords,
                   label=label,
                   popup=popup,
                   icon_url=icon_url,
                   svg=svg,
                   scale=scale,
                   anchor=anchor,
                   rotation=rotation,
                   fill_color=fill_color,
                   stroke_color=stroke_color,
                   stroke_width=stroke_width,
                   radius=radius,
                   extra=style)
        return self._register(m)

    def add_svg_marker(self,
                       coords: tuple[float, float],
                       svg: str,
                       *,
                       anchor: tuple[float, float] = (0.5, 0.5),
                       scale: float = 1.0,
                       **kwargs: Any) -> SvgMarker:
        m = SvgMarker(_new_feature_id(),
                      coords=coords,
                      svg=svg,
                      anchor=anchor,
                      scale=scale,
                      **kwargs)
        return self._register(m)

    def add_line(self,
                 coords: Sequence[tuple[float, float]],
                 *,
                 color: str = '#3b82f6',
                 width: float = 3,
                 dash: Sequence[float] | None = None,
                 popup: str | None = None) -> Line:
        line = Line(_new_feature_id(),
                    coords=list(coords),
                    color=color,
                    width=width,
                    dash=list(dash) if dash else None,
                    popup=popup)
        return self._register(line)

    def add_polygon(self,
                    coords: Sequence[Sequence[tuple[float, float]]] | Sequence[tuple[float, float]],
                    *,
                    fill_color: str = 'rgba(59, 130, 246, 0.3)',
                    stroke_color: str = '#1e3a8a',
                    stroke_width: float = 2,
                    dash: Sequence[float] | None = None,
                    popup: str | None = None) -> Polygon:
        rings = _normalize_polygon_coords(coords)
        poly = Polygon(_new_feature_id(),
                       coords=rings,
                       fill_color=fill_color,
                       stroke_color=stroke_color,
                       stroke_width=stroke_width,
                       dash=list(dash) if dash else None,
                       popup=popup)
        return self._register(poly)

    def clear(self) -> None:
        """Remove all features from this layer."""
        self._features.clear()
        if self._map is not None:
            self._map.run_method('clear_layer', self.id)

    # ------------------------------------------------------------------

    def _register(self, feature: Feature) -> Feature:
        feature._layer = self
        self._features.append(feature)
        if self._map is not None:
            self._map.run_method('add_feature', self.id, feature.to_dict())
        return feature

    def _remove_feature(self, feature: Feature) -> None:
        if feature in self._features:
            self._features.remove(feature)
        if self._map is not None:
            self._map.run_method('remove_feature', self.id, feature.id)


def _normalize_polygon_coords(coords: Any) -> list[list[tuple[float, float]]]:
    """Allow either a single ring (list of ``(lon, lat)``) or list of rings."""
    if not coords:
        return []
    first = coords[0]
    # ring vs. list-of-rings
    if isinstance(first, (list, tuple)) and first and isinstance(first[0], (int, float)):
        return [list(coords)]
    return [list(ring) for ring in coords]
