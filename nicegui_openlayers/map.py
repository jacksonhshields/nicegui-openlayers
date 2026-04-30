from __future__ import annotations

import asyncio
import itertools
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from nicegui.awaitable_response import AwaitableResponse, NullResponse
from nicegui.element import Element
from nicegui.events import GenericEventArguments, handle_event

from .layers import GeoJsonLayer, Layer, OsmLayer, VectorLayer, WmsLayer, XyzLayer
from .presets import BASEMAP_PRESETS

_FRONTEND = Path(__file__).parent / 'frontend'
_id_counter = itertools.count()


def _new_id(prefix: str) -> str:
    return f'{prefix}-{next(_id_counter)}'


class OpenLayersMap(Element,
                    component=str(_FRONTEND / 'openlayers.js'),
                    default_classes='nicegui-openlayers'):
    """Interactive map element backed by OpenLayers.

    Coordinates throughout the API are ``(longitude, latitude)`` in EPSG:4326.
    """

    def __init__(self,
                 *,
                 center: tuple[float, float] = (0.0, 0.0),
                 zoom: float = 2,
                 layer_control: bool = False,
                 projection: str = 'EPSG:3857',
                 custom_projections: Sequence[dict] | None = None) -> None:
        super().__init__()
        self.add_resource(_FRONTEND)

        self._props['initialCenter'] = list(center)
        self._props['initialZoom'] = zoom
        self._props['layerControl'] = layer_control
        self._props['drawControl'] = False
        self._props['drawConfig'] = {
            'layerId': None, 'types': [], 'modify': True, 'snap': True, 'continuous': False,
        }
        self._props['viewProjection'] = projection
        self._props['customProjections'] = list(custom_projections or [])
        self._props['measureControl'] = False
        self._props['measureConfig'] = {
            'types': [], 'units': 'metric', 'persist': True, 'continuous': False,
        }
        self._props['scaleBarConfig'] = None

        self._layers: list[Layer] = []
        self._is_initialized = False
        self._init_event = asyncio.Event()
        self._draw_layer: 'VectorLayer | None' = None

        self._center = tuple(center)
        self._zoom = zoom
        self._projection = projection

        self.on('init', self._handle_init)
        self.on('view_change', self._handle_view_change)
        self.on('feature_click', self._noop)
        self.on('map_click', self._noop)
        self.on('layer_visibility', self._noop)
        self.on('draw_created', self._handle_draw_created)
        self.on('draw_modified', self._handle_draw_modified)
        self.on('draw_deleted', self._handle_draw_deleted)
        self.on('draw_mode', self._noop)
        self.on('measure', self._noop)

    # ------------------------------------------------------------------
    # lifecycle / plumbing
    # ------------------------------------------------------------------

    def _noop(self, _: GenericEventArguments) -> None:
        pass

    def _handle_init(self, _: GenericEventArguments | None = None) -> None:
        self._is_initialized = True
        self._init_event.set()
        for layer in self._layers:
            super().run_method('add_layer', layer.to_dict())
            for feature in layer.features():
                super().run_method('add_feature', layer.id, feature.to_dict())

    async def initialized(self) -> None:
        """Wait for the client to finish initial setup."""
        await self.client.connected()
        await self._init_event.wait()

    def _handle_view_change(self, e: GenericEventArguments) -> None:
        coord = e.args.get('center') or [0, 0]
        self._center = (float(coord[0]), float(coord[1]))
        self._zoom = float(e.args.get('zoom') or self._zoom)

    def run_method(self, name: str, *args: Any, timeout: float = 1) -> AwaitableResponse:
        if not self._is_initialized:
            return NullResponse()
        return super().run_method(name, *args, timeout=timeout)

    # ------------------------------------------------------------------
    # layer factories
    # ------------------------------------------------------------------

    def osm_layer(self, *, title: str = 'OpenStreetMap', **kwargs: Any) -> OsmLayer:
        """Add an OpenStreetMap raster basemap."""
        layer = OsmLayer(_new_id('layer'), title=title, **kwargs)
        return self._register(layer)

    def xyz_layer(self,
                  url: str,
                  *,
                  title: str | None = None,
                  attribution: str | None = None,
                  **kwargs: Any) -> XyzLayer:
        """Add a slippy-map (XYZ) tile layer."""
        layer = XyzLayer(_new_id('layer'),
                         url=url,
                         title=title or 'Tile layer',
                         attribution=attribution,
                         **kwargs)
        return self._register(layer)

    def wms_layer(self,
                  url: str,
                  layers: str,
                  *,
                  title: str | None = None,
                  params: dict | None = None,
                  tiled: bool = True,
                  **kwargs: Any) -> WmsLayer:
        """Add a WMS layer.

        :param url: WMS endpoint URL.
        :param layers: comma-separated layer names (the WMS ``LAYERS`` param).
        :param params: extra WMS request parameters (``VERSION``, ``FORMAT``, ``CRS``...).
        :param tiled: ``True`` for tiled WMS (default), ``False`` for a single image WMS request.
        """
        merged: dict = {'LAYERS': layers}
        if params:
            merged.update(params)
        layer = WmsLayer(_new_id('layer'),
                         url=url,
                         params=merged,
                         title=title or layers,
                         tiled=tiled,
                         **kwargs)
        return self._register(layer)

    def vector_layer(self, *, title: str = 'Vector', **kwargs: Any) -> VectorLayer:
        """Add a vector layer for markers, lines, and polygons."""
        layer = VectorLayer(_new_id('layer'), title=title, **kwargs)
        return self._register(layer)

    def geojson_layer(self,
                      *,
                      data: dict | None = None,
                      url: str | None = None,
                      title: str = 'GeoJSON',
                      popup_property: str | None = None,
                      **kwargs: Any) -> GeoJsonLayer:
        """Add a GeoJSON layer.

        Pass either ``data`` (an inline GeoJSON ``FeatureCollection`` /
        ``Feature`` dict) or ``url`` for the browser to fetch. Set
        ``popup_property`` to the name of a feature property whose value should
        be shown as a popup on click.
        """
        if data is None and url is None:
            raise ValueError('geojson_layer needs either `data` or `url`')
        layer = GeoJsonLayer(_new_id('layer'),
                             data=data,
                             url=url,
                             title=title,
                             popup_property=popup_property,
                             **kwargs)
        return self._register(layer)

    def add_basemap(self,
                    preset: str,
                    *,
                    visible: bool = True,
                    title: str | None = None,
                    **kwargs: Any) -> Layer:
        """Add a built-in basemap by preset name.

        Available presets: ``osm``, ``osm_hot``, ``carto_light``, ``carto_dark``,
        ``esri_world_imagery``, ``opentopomap``.
        Basemaps are added to a single ``Basemaps`` group with exclusive selection.
        """
        if preset not in BASEMAP_PRESETS:
            raise ValueError(f'Unknown basemap preset: {preset!r}. '
                             f'Available: {sorted(BASEMAP_PRESETS)}')
        spec = dict(BASEMAP_PRESETS[preset])
        spec.update(kwargs)
        spec.setdefault('group', 'Basemaps')
        spec.setdefault('exclusive', True)
        spec.setdefault('basemap', True)
        spec['visible'] = visible
        if title:
            spec['title'] = title
        type_ = spec.pop('type')
        if type_ == 'osm':
            layer = OsmLayer(_new_id('layer'), **spec)
        elif type_ == 'xyz':
            url = spec.pop('url')
            layer = XyzLayer(_new_id('layer'), url=url, **spec)
        else:
            raise ValueError(f'Unsupported basemap preset type: {type_}')
        return self._register(layer)

    def _register(self, layer: Layer) -> Layer:
        layer._map = self
        self._layers.append(layer)
        if self._is_initialized:
            super().run_method('add_layer', layer.to_dict())
        return layer

    def remove_layer(self, layer: Layer) -> None:
        """Remove a layer from the map."""
        if layer in self._layers:
            self._layers.remove(layer)
        if self._is_initialized:
            super().run_method('remove_layer', layer.id)

    def layers(self) -> list[Layer]:
        return list(self._layers)

    # ------------------------------------------------------------------
    # view / fit
    # ------------------------------------------------------------------

    def set_view(self,
                 center: tuple[float, float] | None = None,
                 zoom: float | None = None) -> None:
        """Pan/zoom to a new view."""
        if center is not None:
            self._center = tuple(center)
        if zoom is not None:
            self._zoom = zoom
        if self._is_initialized:
            super().run_method('set_view',
                               list(center) if center is not None else None,
                               zoom)

    # ------------------------------------------------------------------
    # projections
    # ------------------------------------------------------------------

    @property
    def projection(self) -> str:
        """The current view projection (EPSG code)."""
        return self._projection

    def define_projection(self,
                          code: str,
                          proj4_def: str,
                          *,
                          extent: Sequence[float] | None = None,
                          world_extent: Sequence[float] | None = None) -> None:
        """Register a custom projection on the client via proj4.

        Units are taken from the proj4 definition string (e.g. ``+units=m``).

        :param code: EPSG code (e.g. ``'EPSG:32756'``).
        :param proj4_def: proj4 definition string (see https://epsg.io).
        :param extent: optional projection extent ``(minx, miny, maxx, maxy)``
            in the projection's units. Used by OpenLayers to derive sensible
            zoom-to-resolution mappings.
        :param world_extent: optional world extent in lon/lat
            ``(minlon, minlat, maxlon, maxlat)``.
        """
        spec = {'code': code, 'proj4': proj4_def}
        if extent is not None:
            spec['extent'] = list(extent)
        if world_extent is not None:
            spec['worldExtent'] = list(world_extent)
        existing = list(self._props.get('customProjections') or [])
        existing = [p for p in existing if p.get('code') != code]
        existing.append(spec)
        self._props['customProjections'] = existing
        if self._is_initialized:
            super().run_method('define_projection', spec)

    def set_projection(self,
                       code: str,
                       *,
                       center: tuple[float, float] | None = None,
                       zoom: float | None = None) -> None:
        """Switch the view to a different projection.

        Custom projections must be registered first with :meth:`define_projection`
        (or passed via ``custom_projections`` in the constructor). The map's
        center is preserved if ``center`` is not given. Vector features are
        rebuilt in the new projection from the original lon/lat coordinates.
        """
        self._projection = code
        self._props['viewProjection'] = code
        if center is not None:
            self._center = tuple(center)
        if zoom is not None:
            self._zoom = zoom
        if self._is_initialized:
            super().run_method('set_view_projection',
                               code,
                               list(center) if center is not None else None,
                               zoom)

    def fit_bounds(self,
                   bounds: tuple[float, float, float, float],
                   *,
                   padding: Sequence[int] | None = None) -> None:
        """Fit the view to ``(min_lon, min_lat, max_lon, max_lat)``."""
        if self._is_initialized:
            super().run_method('fit_bounds', list(bounds),
                               list(padding) if padding else None)

    def fit_layers(self,
                   layers: Iterable[Layer],
                   *,
                   padding: Sequence[int] | None = None) -> None:
        """Fit the view to the combined extent of the given vector layers."""
        ids = [layer.id for layer in layers]
        if self._is_initialized:
            super().run_method('fit_layers', ids,
                               list(padding) if padding else None)

    # ------------------------------------------------------------------
    # scale bar / measurement
    # ------------------------------------------------------------------

    SCALE_BAR_UNITS = ('metric', 'imperial', 'us', 'nautical', 'degrees')

    def scale_bar(self,
                  *,
                  visible: bool = True,
                  units: str = 'metric',
                  bar: bool = False,
                  steps: int = 4,
                  text: bool = False,
                  min_width: int = 80) -> 'OpenLayersMap':
        """Show or hide a scale-line control on the map.

        :param visible: ``False`` removes the control.
        :param units: one of ``'metric'``, ``'imperial'``, ``'us'``,
            ``'nautical'`` or ``'degrees'``.
        :param bar: render as a stepped bar instead of a single line.
        :param steps: number of segments when ``bar=True``.
        :param text: include the scale text alongside the bar.
        :param min_width: minimum width of the control in pixels.
        """
        if units not in self.SCALE_BAR_UNITS:
            raise ValueError(f'units must be one of {self.SCALE_BAR_UNITS}')
        cfg = {
            'visible': visible,
            'units': units,
            'bar': bar,
            'steps': steps,
            'text': text,
            'minWidth': min_width,
        }
        self._props['scaleBarConfig'] = cfg
        if self._is_initialized:
            super().run_method('set_scale_bar', cfg)
        return self

    MEASURE_TYPES = ('Distance', 'Angle')

    def measure_control(self,
                        *,
                        types: Sequence[str] = MEASURE_TYPES,
                        units: str = 'metric',
                        persist: bool = True,
                        continuous: bool = False) -> 'OpenLayersMap':
        """Add measure tools (distance, angle) to the map's toolbar.

        Distances are computed geodesically (great-circle), so the answer
        does not depend on the current view projection. Angles are the
        geodesic angle at the middle vertex of a three-click polyline.

        :param types: any of ``'Distance'``, ``'Angle'``.
        :param units: distance units. One of ``'metric'`` (default; m/km),
            ``'imperial'`` / ``'us'`` (ft/mi), ``'nautical'`` (nmi).
        :param persist: keep finished measurements visible until cleared.
        :param continuous: stay in the same measurement tool after each
            measurement (default: drop back to no tool).
        """
        for t in types:
            if t not in self.MEASURE_TYPES:
                raise ValueError(f'Unsupported measure type: {t!r}')
        if units not in ('metric', 'imperial', 'us', 'nautical'):
            raise ValueError(f'Unsupported measure units: {units!r}')
        self._props['measureControl'] = True
        cfg = {
            'types': list(types),
            'units': units,
            'persist': persist,
            'continuous': continuous,
        }
        self._props['measureConfig'] = cfg
        self.update()
        if self._is_initialized:
            super().run_method('set_measure_config', cfg)
        return self

    def hide_measure_control(self) -> None:
        """Remove the measure toolbar (already-drawn measurements stay)."""
        self._props['measureControl'] = False
        self.update()

    def clear_measurements(self) -> None:
        """Erase all on-screen measurements."""
        if self._is_initialized:
            super().run_method('clearMeasurements')

    def on_measure(self,
                   handler: Callable[[GenericEventArguments], Any]) -> 'OpenLayersMap':
        """Fires when a measurement is finished. ``e.args`` carries
        ``kind`` (``'Distance'`` or ``'Angle'``), ``value`` (metres or
        degrees), ``text`` (formatted), ``coords`` and ``units``.
        """
        self.on('measure', handler)
        return self

    # ------------------------------------------------------------------
    # popups
    # ------------------------------------------------------------------

    def open_popup(self, coord: tuple[float, float], html: str) -> None:
        """Open an ad-hoc popup at the given lon/lat."""
        if self._is_initialized:
            super().run_method('open_popup_at', list(coord), html)

    def close_popup(self) -> None:
        if self._is_initialized:
            super().run_method('close_popup')

    # ------------------------------------------------------------------
    # layer control
    # ------------------------------------------------------------------

    def show_layer_control(self, visible: bool = True) -> None:
        self._props['layerControl'] = visible
        self.update()

    # ------------------------------------------------------------------
    # drawing
    # ------------------------------------------------------------------

    DEFAULT_DRAW_TYPES = ('Point', 'LineString', 'Polygon', 'Rectangle')

    def draw_control(self,
                     *,
                     layer: 'VectorLayer | None' = None,
                     types: Sequence[str] = DEFAULT_DRAW_TYPES,
                     modify: bool = True,
                     snap: bool = True,
                     continuous: bool = False,
                     title: str = 'Drawn') -> 'VectorLayer':
        """Enable an interactive drawing toolbar.

        :param layer: the vector layer that drawn features are added to. If
            ``None`` a new layer titled ``title`` is created automatically.
        :param types: allowed shapes. Any combination of ``'Point'``,
            ``'LineString'``, ``'Polygon'``, ``'Rectangle'``.
        :param modify: include an edit tool that drags vertices.
        :param snap: snap to existing vertices while drawing/editing.
        :param continuous: stay in the same draw tool after finishing a shape
            (default: drop back to no tool).
        :returns: the vector layer that drawn features are written to.
        """
        for t in types:
            if t not in {'Point', 'LineString', 'Polygon', 'Rectangle'}:
                raise ValueError(f'Unsupported draw type: {t!r}')
        if layer is None:
            layer = self.vector_layer(title=title, group='Drawn')
        self._draw_layer = layer
        self._props['drawControl'] = True
        cfg = {
            'layerId': layer.id,
            'types': list(types),
            'modify': modify,
            'snap': snap,
            'continuous': continuous,
        }
        self._props['drawConfig'] = cfg
        self.update()
        if self._is_initialized:
            super().run_method('set_draw_config', cfg)
        return layer

    def hide_draw_control(self) -> None:
        self._props['drawControl'] = False
        self.update()
        if self._is_initialized:
            super().run_method('set_active_draw_mode', None)

    def draw(self, mode: str | None) -> None:
        """Programmatically activate a draw tool, e.g. ``map.draw('Polygon')``.

        Pass ``None`` to deactivate.
        """
        if self._is_initialized:
            super().run_method('set_active_draw_mode', mode)

    def stop_drawing(self) -> None:
        self.draw(None)

    def clear_drawn(self) -> None:
        if self._draw_layer is not None:
            self._draw_layer.clear()

    @property
    def drawn(self) -> list:
        """List of features currently in the draw layer."""
        return list(self._draw_layer.features()) if self._draw_layer else []

    # event helpers

    def on_draw(self, handler: Callable[[GenericEventArguments], Any]) -> 'OpenLayersMap':
        """Fires when the user finishes drawing a new feature."""
        self.on('draw_created', handler)
        return self

    def on_modify(self, handler: Callable[[GenericEventArguments], Any]) -> 'OpenLayersMap':
        """Fires when an existing drawn feature has been edited."""
        self.on('draw_modified', handler)
        return self

    def on_delete(self, handler: Callable[[GenericEventArguments], Any]) -> 'OpenLayersMap':
        """Fires when a drawn feature is deleted (toolbar or programmatic)."""
        self.on('draw_deleted', handler)
        return self

    # internal handlers

    def _handle_draw_created(self, e: GenericEventArguments) -> None:
        if self._draw_layer is None:
            return
        # late import to avoid circular ref at module load
        from .features import Line, Marker, Polygon as PolygonFeat
        args = e.args or {}
        ftype = args.get('type')
        coords = args.get('coords')
        fid = args.get('feature_id')
        if not (ftype and fid and coords is not None):
            return
        if ftype == 'marker':
            feat: Any = Marker(fid, coords=tuple(coords))
        elif ftype == 'line':
            feat = Line(fid, coords=[tuple(c) for c in coords])
        elif ftype == 'polygon':
            feat = PolygonFeat(fid, coords=[[tuple(c) for c in ring] for ring in coords])
        else:
            return
        feat._layer = self._draw_layer
        self._draw_layer._features.append(feat)

    def _handle_draw_modified(self, e: GenericEventArguments) -> None:
        if self._draw_layer is None:
            return
        args = e.args or {}
        fid = args.get('feature_id')
        coords = args.get('coords')
        if fid is None or coords is None:
            return
        feat = next((f for f in self._draw_layer.features() if f.id == fid), None)
        if feat is None:
            return
        if hasattr(feat, 'coords'):
            if isinstance(coords[0], list) and isinstance(coords[0][0], list):
                feat.coords = [[tuple(c) for c in ring] for ring in coords]
            elif isinstance(coords[0], list):
                feat.coords = [tuple(c) for c in coords]
            else:
                feat.coords = tuple(coords)

    def _handle_draw_deleted(self, e: GenericEventArguments) -> None:
        if self._draw_layer is None:
            return
        fid = (e.args or {}).get('feature_id')
        if fid is None:
            return
        feats = self._draw_layer._features
        for i, f in enumerate(list(feats)):
            if f.id == fid:
                feats.pop(i)
                break

    # ------------------------------------------------------------------
    # event helpers
    # ------------------------------------------------------------------

    def on_feature_click(self,
                         handler: Callable[[GenericEventArguments], Any]) -> 'OpenLayersMap':
        self.on('feature_click', handler)
        return self

    def on_map_click(self,
                     handler: Callable[[GenericEventArguments], Any]) -> 'OpenLayersMap':
        self.on('map_click', handler)
        return self

    def on_view_change(self,
                       handler: Callable[[GenericEventArguments], Any]) -> 'OpenLayersMap':
        self.on('view_change', handler)
        return self

    @property
    def center(self) -> tuple[float, float]:
        return self._center

    @property
    def zoom(self) -> float:
        return self._zoom


def openlayers(**kwargs: Any) -> OpenLayersMap:
    """Shorthand factory matching NiceGUI's ``ui.foo()`` style."""
    return OpenLayersMap(**kwargs)
