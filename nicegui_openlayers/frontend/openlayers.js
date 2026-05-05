import { loadResource } from "../../static/utils/resources.js";

let olLoadPromise = null;
function ensureOpenLayers(resourcePath) {
  if (window.ol) return Promise.resolve(window.ol);
  if (olLoadPromise) return olLoadPromise;
  const base = window.path_prefix + resourcePath;
  olLoadPromise = (async () => {
    await loadResource(`${base}/ol/ol.css`);
    await loadResource(`${base}/ol/ol.js`);
    await loadResource(`${base}/openlayers.css`);
    return window.ol;
  })();
  return olLoadPromise;
}

let proj4LoadPromise = null;
function ensureProj4(resourcePath) {
  if (window.proj4) return Promise.resolve(window.proj4);
  if (proj4LoadPromise) return proj4LoadPromise;
  const base = window.path_prefix + resourcePath;
  proj4LoadPromise = (async () => {
    await loadResource(`${base}/proj4/proj4.js`);
    if (window.ol && window.ol.proj && window.ol.proj.proj4 && window.proj4) {
      window.ol.proj.proj4.register(window.proj4);
    }
    return window.proj4;
  })();
  return proj4LoadPromise;
}

export default {
  template: `
    <div class="nol-wrap">
      <div ref="mapEl" class="nol-map"></div>
      <div ref="popupEl" class="nol-popup" v-show="popupVisible">
        <button class="nol-popup-close" @click="closePopup">×</button>
        <div class="nol-popup-content" v-html="popupHtml"></div>
      </div>
      <div ref="measureTipEl" class="nol-measure-tip"
           v-show="measureTooltipText">{{ measureTooltipText }}</div>
      <div v-if="(drawControl && drawConfig.types.length) || (measureControl && measureConfig.types.length)"
           class="nol-toolbar">
        <button v-for="t in drawConfig.types" :key="t"
                class="nol-tool" :class="{active: activeMode === t}"
                :title="toolLabel(t)"
                @click="setMode(activeMode === t ? null : t)"
                v-html="toolIcon(t)"></button>
        <div v-if="drawControl && drawConfig.modify" class="nol-tool-sep"></div>
        <button v-if="drawControl && drawConfig.modify" class="nol-tool"
                :class="{active: activeMode === 'Edit'}"
                title="Edit (drag vertices)"
                @click="setMode(activeMode === 'Edit' ? null : 'Edit')"
                v-html="toolIcon('Edit')"></button>
        <button v-if="drawControl && drawConfig.modify" class="nol-tool"
                :class="{active: activeMode === 'Delete'}"
                title="Delete (click feature)"
                @click="setMode(activeMode === 'Delete' ? null : 'Delete')"
                v-html="toolIcon('Delete')"></button>
        <div v-if="drawControl" class="nol-tool-sep"></div>
        <button v-if="drawControl" class="nol-tool" title="Clear drawn"
                @click="clearDrawLayer" v-html="toolIcon('Clear')"></button>
        <div v-if="drawControl && measureControl && measureConfig.types.length" class="nol-tool-sep"></div>
        <button v-for="t in (measureControl ? measureConfig.types : [])" :key="'m-'+t"
                class="nol-tool" :class="{active: activeMode === ('Measure-'+t)}"
                :title="measureLabel(t)"
                @click="setMode(activeMode === ('Measure-'+t) ? null : ('Measure-'+t))"
                v-html="measureIcon(t)"></button>
        <button v-if="measureControl && measureConfig.types.length" class="nol-tool"
                title="Clear measurements" @click="clearMeasurements"
                v-html="toolIcon('Clear')"></button>
      </div>
      <slot></slot>
      <div v-if="layerControl" class="nol-layers">
        <div class="nol-layers-header" @click="layerPanelOpen = !layerPanelOpen">
          <span class="nol-group-caret">{{ layerPanelOpen ? '▼' : '▶' }}</span>
          <span>Layers</span>
        </div>
        <div v-show="layerPanelOpen" class="nol-layers-body">
          <div v-for="group in layerGroups" :key="group.name" class="nol-group">
            <div class="nol-group-header" @click="toggleGroup(group.name)">
              <span class="nol-group-caret">{{ groupOpen[group.name] === false ? '▶' : '▼' }}</span>
              <span>{{ group.name }}</span>
            </div>
            <div v-show="groupOpen[group.name] !== false" class="nol-group-body">
              <div v-for="l in group.layers" :key="l.id" class="nol-layer-row">
                <input v-if="group.exclusive"
                       type="radio"
                       :name="'nol-grp-' + group.name"
                       :checked="l.visible"
                       @change="onExclusivePick(group.name, l.id)" />
                <input v-else
                       type="checkbox"
                       :checked="l.visible"
                       @change="onToggleVisible(l.id, $event.target.checked)" />
                <span class="nol-layer-name" :title="l.title">{{ l.title }}</span>
                <input type="range"
                       min="0" max="1" step="0.05"
                       :value="l.opacity"
                       @input="onSetOpacity(l.id, parseFloat($event.target.value))"
                       class="nol-layer-opacity" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  props: {
    initialCenter: { type: Array, default: () => [0, 0] },
    initialZoom: { type: Number, default: 2 },
    layerControl: { type: Boolean, default: false },
    drawControl: { type: Boolean, default: false },
    drawConfig: {
      type: Object,
      default: () => ({ layerId: null, types: [], modify: true, snap: true, continuous: false }),
    },
    viewProjection: { type: String, default: "EPSG:3857" },
    customProjections: { type: Array, default: () => [] },
    measureControl: { type: Boolean, default: false },
    measureConfig: {
      type: Object,
      default: () => ({ types: [], units: "metric", persist: true }),
    },
    scaleBarConfig: { type: Object, default: () => null },
    resourcePath: { type: String, default: "" },
  },
  data() {
    return {
      map: null,
      popupOverlay: null,
      popupVisible: false,
      popupHtml: "",
      layerPanelOpen: true,
      groupOpen: {},
      olLayers: {},          // id -> ol.layer.*
      olFeatures: {},        // layerId -> { featureId -> ol.Feature }
      featureSpecs: {},      // layerId -> { featureId -> spec snapshot }
      geojsonSpecs: {},      // layerId -> last full spec for geojson layers
      layerMeta: {},         // id -> {title, group, exclusive, visible, opacity, type, basemap}
      layerOrder: [],        // insertion order
      groupOrder: [],
      _resizeObs: null,
      activeMode: null,
      drawInteraction: null,
      modifyInteraction: null,
      snapInteraction: null,
      selectInteraction: null,
      _deleteClickKey: null,
      _drawCounter: 0,
      // mirror of the viewProjection prop. Props are read-only, so we hold a
      // mutable copy here that set_view_projection() can update.
      currentProjection: this.$props.viewProjection,
      // proj4 defs we've registered (code -> spec) so we can re-apply them
      // defensively when switching views.
      _projDefs: {},
      // measure tooling
      _measureLayer: null,
      _measureTooltipOverlay: null,
      measureTooltipText: "",
      _measureSketchListener: null,
      _measureCounter: 0,
      _scaleLine: null,
      _customControls: {},     // id -> { control: ol.control.Control, spec }
      _customControlCounts: { 'top-left': 0, 'top-right': 0, 'bottom-left': 0, 'bottom-right': 0 },
    };
  },
  computed: {
    layerGroups() {
      const seen = {};
      for (const id of this.layerOrder) {
        const meta = this.layerMeta[id];
        if (!meta) continue;
        const g = meta.group;
        if (!seen[g]) seen[g] = { name: g, exclusive: !!meta.exclusive, layers: [] };
        seen[g].layers.push({ id, ...meta });
      }
      const ordered = [];
      for (const name of this.groupOrder) if (seen[name]) { ordered.push(seen[name]); delete seen[name]; }
      for (const name in seen) ordered.push(seen[name]);
      return ordered;
    },
  },
  async mounted() {
    await this.$nextTick();
    await ensureOpenLayers(this.resourcePath);
    if (this.customProjections.length || this.currentProjection !== "EPSG:3857") {
      await ensureProj4(this.resourcePath);
      for (const def of this.customProjections) this._registerProjection(def);
    }
    this.initMap();
    const tryEmit = setInterval(() => {
      if (window.socket && window.socket.id !== undefined) {
        this.$emit("init");
        clearInterval(tryEmit);
      }
    }, 80);
    this._resizeObs = new ResizeObserver(() => {
      if (this.map) this.map.updateSize();
    });
    this._resizeObs.observe(this.$el);
    this._keyHandler = (e) => {
      if (e.key === "Escape" && this.drawInteraction) {
        this.drawInteraction.abortDrawing();
      } else if ((e.key === "Backspace" || e.key === "Delete") && this.drawInteraction) {
        this.drawInteraction.removeLastPoint();
      }
    };
    document.addEventListener("keydown", this._keyHandler);
  },
  beforeUnmount() {
    if (this._resizeObs) this._resizeObs.disconnect();
    if (this._keyHandler) document.removeEventListener("keydown", this._keyHandler);
    if (this.map) this.map.setTarget(null);
  },
  methods: {
    initMap() {
      const { Map, View, Overlay } = ol;
      this.map = new Map({
        target: this.$refs.mapEl,
        controls: ol.control.defaults.defaults({ attributionOptions: { collapsible: true } }),
        view: this._buildView(this.initialCenter, this.initialZoom, this.currentProjection),
      });
      this.popupOverlay = new Overlay({
        element: this.$refs.popupEl,
        positioning: "bottom-center",
        stopEvent: true,
        offset: [0, -12],
      });
      this.map.addOverlay(this.popupOverlay);
      this._measureTooltipOverlay = new Overlay({
        element: this.$refs.measureTipEl,
        positioning: "bottom-center",
        stopEvent: false,
        offset: [0, -10],
      });
      this.map.addOverlay(this._measureTooltipOverlay);
      if (this.scaleBarConfig) this._applyScaleBar(this.scaleBarConfig);
      this.map.on("singleclick", (e) => this.handleClick(e));
      this.map.on("pointermove", (e) => {
        if (e.dragging) return;
        const hit = this.map.hasFeatureAtPixel(e.pixel);
        this.map.getTargetElement().style.cursor = hit ? "pointer" : "";
      });
      this.map.on("moveend", () => {
        const v = this.map.getView();
        const center = v.getCenter();
        this.$emit("view_change", {
          center: center ? ol.proj.toLonLat(center, this.currentProjection) : [0, 0],
          zoom: v.getZoom(),
          projection: this.currentProjection,
        });
      });
    },

    _registerProjection(def) {
      if (!window.proj4 || !def || !def.code || !def.proj4) return false;
      this._projDefs[def.code] = def;
      window.proj4.defs(def.code, def.proj4);
      window.ol.proj.proj4.register(window.proj4);
      const olProj = ol.proj.get(def.code);
      if (!olProj) {
        console.warn(
          `nicegui-openlayers: projection ${def.code} failed to register with OpenLayers`,
        );
        return false;
      }
      // Units come from the proj4 definition automatically; only extent/
      // world-extent need to be applied after the fact (OL has no setUnits).
      if (def.extent) olProj.setExtent(def.extent);
      if (def.worldExtent) olProj.setWorldExtent(def.worldExtent);
      return true;
    },

    async _ensureProjection(code) {
      if (code === "EPSG:3857" || code === "EPSG:4326") return ol.proj.get(code);
      await ensureProj4(this.resourcePath);
      let olProj = ol.proj.get(code);
      if (olProj) return olProj;
      const def = this._projDefs[code];
      if (def) this._registerProjection(def);
      olProj = ol.proj.get(code);
      if (!olProj) {
        console.error(
          `nicegui-openlayers: cannot use unregistered projection ${code}. ` +
          `Call define_projection() or pass it via custom_projections=.`,
        );
      }
      return olProj;
    },

    _buildView(lonLatCenter, zoom, projection) {
      // Resolve to a Projection object so OL never silently falls back to the
      // default when a string code isn't yet in its registry.
      const olProj = ol.proj.get(projection) || projection;
      return new ol.View({
        center: ol.proj.fromLonLat(lonLatCenter, olProj),
        zoom: zoom,
        projection: olProj,
      });
    },

    async define_projection(def) {
      await ensureProj4(this.resourcePath);
      this._registerProjection(def);
    },

    async set_view_projection(code, lonLatCenter, zoom) {
      const olProj = await this._ensureProjection(code);
      if (!olProj) return;  // bail rather than silently render garbage
      // capture current state in lon/lat BEFORE switching the local proj
      const v = this.map.getView();
      const curCenter = v.getCenter();
      const ll = lonLatCenter || (curCenter
        ? ol.proj.toLonLat(curCenter, this.currentProjection)
        : this.initialCenter);
      const z = zoom != null ? zoom : v.getZoom();
      // disarm any active draw tool so its bound view goes away cleanly
      const wasMode = this.activeMode;
      if (wasMode) this._deactivateInteractions();
      this.currentProjection = code;
      this.map.setView(this._buildView(ll, z, code));
      // rebuild vector features so their geometries are in the new projection
      for (const layerId of Object.keys(this.olLayers)) {
        const meta = this.layerMeta[layerId];
        if (!meta) continue;
        if (meta.type === "vector") this._rebuildVectorLayer(layerId);
        else if (meta.type === "geojson") this._reloadGeoJsonLayer(layerId);
      }
      // re-arm the previous draw tool against the new view
      if (wasMode) this.setMode(wasMode);
    },

    _rebuildVectorLayer(layerId) {
      const layer = this.olLayers[layerId];
      if (!layer || !(layer instanceof ol.layer.Vector)) return;
      const src = layer.getSource();
      src.clear();
      const specs = this.featureSpecs[layerId] || {};
      this.olFeatures[layerId] = {};
      for (const fid of Object.keys(specs)) {
        const spec = { ...specs[fid], id: fid };
        const feat = this._buildFeature(spec);
        if (!feat) continue;
        feat.setId(fid);
        feat.set("nolFeatureId", fid);
        feat.set("nolLayerId", layerId);
        if (spec.popup != null) feat.set("nolPopup", spec.popup);
        src.addFeature(feat);
        this.olFeatures[layerId][fid] = feat;
      }
    },

    _reloadGeoJsonLayer(layerId) {
      const layer = this.olLayers[layerId];
      const spec = this.geojsonSpecs[layerId];
      if (!layer || !spec) return;
      this._loadGeoJson(layer, spec);
    },

    // ===== Layers =====

    add_layer(spec) {
      const layer = this._buildLayer(spec);
      if (!layer) return;
      layer.set("nolId", spec.id);
      if (spec.opacity != null) layer.setOpacity(spec.opacity);
      if (spec.visible != null) layer.setVisible(spec.visible);
      if (spec.zIndex != null) layer.setZIndex(spec.zIndex);
      this.olLayers[spec.id] = layer;
      this.olFeatures[spec.id] = {};
      this.featureSpecs[spec.id] = {};
      this.map.addLayer(layer);

      const group = spec.group || (spec.basemap ? "Basemaps" : (spec.type === "vector" ? "Overlays" : "Layers"));
      this.layerMeta[spec.id] = {
        title: spec.title || spec.id,
        group,
        exclusive: !!spec.exclusive,
        visible: spec.visible !== false,
        opacity: spec.opacity != null ? spec.opacity : 1,
        type: spec.type,
        basemap: !!spec.basemap,
      };
      if (!this.layerOrder.includes(spec.id)) this.layerOrder.push(spec.id);
      if (!this.groupOrder.includes(group)) this.groupOrder.push(group);
    },

    _buildLayer(spec) {
      const o = ol;
      const sourceOptions = spec.sourceOptions || {};
      if (spec.type === "osm") {
        return new o.layer.Tile({ source: new o.source.OSM(sourceOptions) });
      }
      if (spec.type === "xyz") {
        return new o.layer.Tile({
          source: new o.source.XYZ({
            url: spec.url,
            attributions: spec.attribution,
            crossOrigin: spec.crossOrigin,
            ...sourceOptions,
          }),
        });
      }
      if (spec.type === "wms") {
        const opts = {
          url: spec.url,
          params: spec.params || {},
          crossOrigin: spec.crossOrigin,
          serverType: spec.serverType,
          ...sourceOptions,
        };
        if (spec.tiled === false) {
          return new o.layer.Image({ source: new o.source.ImageWMS(opts) });
        }
        return new o.layer.Tile({ source: new o.source.TileWMS(opts) });
      }
      if (spec.type === "vector") {
        return new o.layer.Vector({ source: new o.source.Vector({}) });
      }
      if (spec.type === "geojson") {
        const layer = new o.layer.Vector({ source: new o.source.Vector({}) });
        layer.setStyle(this._buildGeoJsonStyle(spec));
        this.geojsonSpecs[spec.id] = { ...spec };
        this._loadGeoJson(layer, spec);
        return layer;
      }
      console.warn("nicegui-openlayers: unknown layer type", spec.type);
      return null;
    },

    _buildGeoJsonStyle(spec) {
      const { Style, Stroke, Fill } = ol.style;
      const Circle = ol.style.Circle;
      const stroke = new Stroke({
        color: spec.strokeColor || "#1e3a8a",
        width: spec.strokeWidth != null ? spec.strokeWidth : 2,
        lineDash: spec.dash || undefined,
      });
      const fill = new Fill({ color: spec.fillColor || "rgba(59, 130, 246, 0.3)" });
      const pointStyle = new Style({
        image: new Circle({ radius: spec.markerRadius || 6, fill, stroke }),
      });
      const lineStyle = new Style({ stroke });
      const polyStyle = new Style({ stroke, fill });
      return (feature) => {
        const t = feature.getGeometry().getType();
        if (t === "Point" || t === "MultiPoint") return pointStyle;
        if (t === "LineString" || t === "MultiLineString") return lineStyle;
        return polyStyle;
      };
    },

    _loadGeoJson(layer, spec) {
      const src = layer.getSource();
      src.clear();
      const fmt = new ol.format.GeoJSON({
        dataProjection: spec.dataProjection || "EPSG:4326",
        featureProjection: this.currentProjection,
      });
      const tag = (feats) => {
        feats.forEach((f) => {
          f.set("nolLayerId", spec.id);
          if (spec.popupProperty) {
            const v = f.get(spec.popupProperty);
            if (v != null) f.set("nolPopup", String(v));
          }
        });
        return feats;
      };
      if (spec.data) {
        try {
          src.addFeatures(tag(fmt.readFeatures(spec.data)));
        } catch (err) {
          console.warn("nicegui-openlayers: invalid GeoJSON", err);
        }
      } else if (spec.url) {
        const url = spec.url;
        fetch(url)
          .then((r) => r.json())
          .then((data) => {
            // ignore stale fetches if a newer load was started in the meantime
            const cur = this.geojsonSpecs[spec.id];
            if (!cur || cur.url !== url) return;
            src.addFeatures(tag(fmt.readFeatures(data)));
          })
          .catch((err) => console.warn("nicegui-openlayers: geojson fetch failed", err));
      }
    },

    update_geojson(layerId, patch) {
      const layer = this.olLayers[layerId];
      if (!layer || !(layer instanceof ol.layer.Vector)) return;
      const merged = { ...(this.geojsonSpecs[layerId] || {}), ...patch, id: layerId };
      this.geojsonSpecs[layerId] = merged;
      if ("data" in patch || "url" in patch) {
        this._loadGeoJson(layer, merged);
      }
      const styleKeys = ["strokeColor", "strokeWidth", "fillColor", "markerRadius", "dash"];
      if (styleKeys.some((k) => k in patch)) {
        layer.setStyle(this._buildGeoJsonStyle(merged));
      }
    },

    remove_layer(id) {
      const layer = this.olLayers[id];
      if (!layer) return;
      this.map.removeLayer(layer);
      delete this.olLayers[id];
      delete this.olFeatures[id];
      delete this.featureSpecs[id];
      delete this.geojsonSpecs[id];
      delete this.layerMeta[id];
      this.layerOrder = this.layerOrder.filter((x) => x !== id);
    },

    set_layer_visible(id, visible) {
      const layer = this.olLayers[id];
      const meta = this.layerMeta[id];
      if (!layer || !meta) return;
      if (meta.exclusive && visible) {
        for (const oid of this.layerOrder) {
          const om = this.layerMeta[oid];
          if (om && om.group === meta.group && oid !== id) {
            this.olLayers[oid].setVisible(false);
            om.visible = false;
          }
        }
      }
      layer.setVisible(visible);
      meta.visible = visible;
    },

    set_layer_opacity(id, opacity) {
      const layer = this.olLayers[id];
      if (!layer) return;
      layer.setOpacity(opacity);
      if (this.layerMeta[id]) this.layerMeta[id].opacity = opacity;
    },

    set_layer_z_index(id, zIndex) {
      const layer = this.olLayers[id];
      if (layer) layer.setZIndex(zIndex);
    },

    set_layer_source_options(id, sourceOptions) {
      const layer = this.olLayers[id];
      if (!layer) return;
      const src = layer.getSource();
      if (src && typeof src.updateParams === "function" && sourceOptions.params) {
        src.updateParams(sourceOptions.params);
      }
      if (src && typeof src.setUrl === "function" && sourceOptions.url) {
        src.setUrl(sourceOptions.url);
      }
    },

    // ===== Features =====

    add_feature(layerId, spec) {
      const layer = this.olLayers[layerId];
      if (!layer || !(layer instanceof ol.layer.Vector)) {
        console.warn(`nicegui-openlayers: layer ${layerId} not a vector layer`);
        return;
      }
      const feat = this._buildFeature(spec);
      if (!feat) return;
      feat.setId(spec.id);
      feat.set("nolFeatureId", spec.id);
      feat.set("nolLayerId", layerId);
      if (spec.popup != null) feat.set("nolPopup", spec.popup);
      layer.getSource().addFeature(feat);
      this.olFeatures[layerId][spec.id] = feat;
      this.featureSpecs[layerId][spec.id] = { ...spec };
    },

    _buildFeature(spec) {
      const { Feature } = ol;
      const { Point, LineString, Polygon } = ol.geom;
      const proj = this.currentProjection;
      const toView = (c) => ol.proj.fromLonLat(c, proj);
      let feat;
      if (spec.type === "marker") {
        feat = new Feature({ geometry: new Point(toView(spec.coords)) });
      } else if (spec.type === "line") {
        feat = new Feature({
          geometry: new LineString(spec.coords.map(toView)),
        });
      } else if (spec.type === "polygon") {
        feat = new Feature({
          geometry: new Polygon(spec.coords.map((ring) => ring.map(toView))),
        });
      } else {
        return null;
      }
      feat.setStyle(this._buildStyle(spec));
      return feat;
    },

    _buildStyle(spec) {
      const { Style, Icon, Stroke, Fill, Text } = ol.style;
      const Circle = ol.style.Circle;
      if (spec.type === "marker") {
        let image;
        if (spec.svg) {
          const svgUrl = "data:image/svg+xml;utf8," + encodeURIComponent(spec.svg);
          image = new Icon({
            src: svgUrl,
            scale: spec.scale != null ? spec.scale : 1,
            anchor: spec.anchor || [0.5, 1],
            rotation: spec.rotation || 0,
          });
        } else if (spec.iconUrl) {
          image = new Icon({
            src: spec.iconUrl,
            scale: spec.scale != null ? spec.scale : 1,
            anchor: spec.anchor || [0.5, 1],
            rotation: spec.rotation || 0,
          });
        } else {
          image = new Circle({
            radius: spec.radius || 7,
            fill: new Fill({ color: spec.fillColor || "#3b82f6" }),
            stroke: new Stroke({
              color: spec.strokeColor || "#1e3a8a",
              width: spec.strokeWidth != null ? spec.strokeWidth : 1,
            }),
          });
        }
        const styleOpts = { image };
        if (spec.label) {
          styleOpts.text = new Text({
            text: spec.label,
            offsetY: spec.labelOffsetY != null ? spec.labelOffsetY : -18,
            offsetX: spec.labelOffsetX || 0,
            font: spec.labelFont || "bold 12px sans-serif",
            fill: new Fill({ color: spec.labelColor || "#000" }),
            stroke: new Stroke({ color: spec.labelStroke || "#fff", width: 3 }),
          });
        }
        return new Style(styleOpts);
      }
      if (spec.type === "line") {
        return new Style({
          stroke: new Stroke({
            color: spec.color || "#3b82f6",
            width: spec.width || 3,
            lineDash: spec.dash || undefined,
          }),
        });
      }
      if (spec.type === "polygon") {
        return new Style({
          stroke: new Stroke({
            color: spec.strokeColor || "#1e3a8a",
            width: spec.strokeWidth != null ? spec.strokeWidth : 2,
            lineDash: spec.dash || undefined,
          }),
          fill: new Fill({
            color: spec.fillColor || "rgba(59, 130, 246, 0.3)",
          }),
        });
      }
    },

    update_feature(layerId, featureId, patch) {
      const feat = this.olFeatures[layerId]?.[featureId];
      if (!feat) return;
      const { Point, LineString, Polygon } = ol.geom;
      const proj = this.currentProjection;
      const toView = (c) => ol.proj.fromLonLat(c, proj);
      const merged = { ...this.featureSpecs[layerId][featureId], ...patch };

      if (patch.coords !== undefined) {
        if (merged.type === "marker") {
          feat.setGeometry(new Point(toView(merged.coords)));
        } else if (merged.type === "line") {
          feat.setGeometry(new LineString(merged.coords.map(toView)));
        } else if (merged.type === "polygon") {
          feat.setGeometry(new Polygon(merged.coords.map((ring) => ring.map(toView))));
        }
      }
      const styleKeys = [
        "color", "width", "dash",
        "fillColor", "strokeColor", "strokeWidth",
        "svg", "iconUrl", "scale", "anchor", "rotation",
        "label", "labelColor", "labelStroke", "labelFont", "labelOffsetX", "labelOffsetY",
        "radius",
      ];
      if (styleKeys.some((k) => k in patch)) {
        feat.setStyle(this._buildStyle(merged));
      }
      if ("popup" in patch) {
        feat.set("nolPopup", patch.popup);
      }
      this.featureSpecs[layerId][featureId] = merged;
    },

    remove_feature(layerId, featureId) {
      const feat = this.olFeatures[layerId]?.[featureId];
      if (!feat) return;
      this.olLayers[layerId].getSource().removeFeature(feat);
      delete this.olFeatures[layerId][featureId];
      delete this.featureSpecs[layerId][featureId];
    },

    clear_layer(layerId) {
      const layer = this.olLayers[layerId];
      if (!layer || !(layer instanceof ol.layer.Vector)) return;
      layer.getSource().clear();
      this.olFeatures[layerId] = {};
      this.featureSpecs[layerId] = {};
    },

    // ===== Popups =====

    open_popup_at(coord, html) {
      this.popupHtml = html;
      this.popupVisible = true;
      this.popupOverlay.setPosition(ol.proj.fromLonLat(coord, this.currentProjection));
    },

    open_popup_for_feature(layerId, featureId) {
      const feat = this.olFeatures[layerId]?.[featureId];
      if (!feat) return;
      const html = feat.get("nolPopup");
      if (!html) return;
      const geom = feat.getGeometry();
      let coord;
      if (geom.getType() === "Point") coord = geom.getCoordinates();
      else coord = ol.extent.getCenter(geom.getExtent());
      this.popupHtml = html;
      this.popupVisible = true;
      this.popupOverlay.setPosition(coord);
    },

    closePopup() {
      this.popupVisible = false;
      this.popupOverlay.setPosition(undefined);
    },
    close_popup() { this.closePopup(); },

    // ===== View =====

    set_view(center, zoom) {
      const view = this.map.getView();
      if (center) view.setCenter(ol.proj.fromLonLat(center, this.currentProjection));
      if (zoom != null) view.setZoom(zoom);
    },

    fit_bounds(bounds, padding) {
      const ext = ol.proj.transformExtent(bounds, "EPSG:4326", this.currentProjection);
      this.map.getView().fit(ext, {
        padding: padding || [40, 40, 40, 40],
        duration: 300,
      });
    },

    fit_layers(layerIds, padding) {
      let extent = ol.extent.createEmpty();
      let any = false;
      for (const id of layerIds) {
        const layer = this.olLayers[id];
        const src = layer && layer.getSource && layer.getSource();
        if (src && typeof src.getExtent === "function") {
          const e = src.getExtent();
          if (e && isFinite(e[0]) && isFinite(e[1])) {
            extent = ol.extent.extend(extent, e);
            any = true;
          }
        }
      }
      if (any && !ol.extent.isEmpty(extent)) {
        this.map.getView().fit(extent, {
          padding: padding || [40, 40, 40, 40],
          duration: 300,
        });
      }
    },

    // ===== Layer control UI handlers =====

    toggleGroup(name) {
      this.groupOpen = { ...this.groupOpen, [name]: !(this.groupOpen[name] !== false) };
    },
    onToggleVisible(id, visible) {
      this.set_layer_visible(id, visible);
      this.$emit("layer_visibility", { id, visible });
    },
    onSetOpacity(id, opacity) {
      this.set_layer_opacity(id, opacity);
    },
    onExclusivePick(group, id) {
      for (const oid of this.layerOrder) {
        const m = this.layerMeta[oid];
        if (m && m.group === group) {
          const v = oid === id;
          this.olLayers[oid].setVisible(v);
          m.visible = v;
        }
      }
      this.$emit("layer_visibility", { id, visible: true, group });
    },

    // ===== Drawing =====

    set_draw_config(cfg) {
      this.drawConfig = { ...this.drawConfig, ...cfg };
      // re-arm if a tool was active and the draw layer changed
      if (this.activeMode) this.setMode(this.activeMode);
    },

    set_active_draw_mode(mode) {
      this.setMode(mode);
    },

    setMode(mode) {
      this._deactivateInteractions();
      this.activeMode = mode;
      if (!mode) {
        this.$emit("draw_mode", { mode: null });
        return;
      }
      if (mode.startsWith("Measure-")) {
        this._activateMeasure(mode.slice("Measure-".length));
        this.$emit("draw_mode", { mode });
        return;
      }
      const layerId = this.drawConfig.layerId;
      const layer = layerId && this.olLayers[layerId];
      if (!layer || !(layer instanceof ol.layer.Vector)) {
        console.warn("nicegui-openlayers: draw layer is not a vector layer");
        this.activeMode = null;
        return;
      }
      if (mode === "Edit") this._activateModify(layer);
      else if (mode === "Delete") this._activateDelete(layer);
      else this._activateDraw(layer, mode);
      this.$emit("draw_mode", { mode });
    },

    _deactivateInteractions() {
      for (const key of ["drawInteraction", "modifyInteraction", "snapInteraction", "selectInteraction"]) {
        if (this[key]) {
          this.map.removeInteraction(this[key]);
          this[key] = null;
        }
      }
      if (this._deleteClickKey) {
        ol.Observable.unByKey(this._deleteClickKey);
        this._deleteClickKey = null;
      }
      if (this._measureSketchListener) {
        ol.Observable.unByKey(this._measureSketchListener);
        this._measureSketchListener = null;
      }
      this.measureTooltipText = "";
      if (this._measureTooltipOverlay) this._measureTooltipOverlay.setPosition(undefined);
    },

    // ===== Scale bar =====

    set_scale_bar(cfg) { this._applyScaleBar(cfg); },

    _applyScaleBar(cfg) {
      if (this._scaleLine) {
        this.map.removeControl(this._scaleLine);
        this._scaleLine = null;
      }
      if (!cfg || cfg.visible === false) return;
      this._scaleLine = new ol.control.ScaleLine({
        units: cfg.units || "metric",
        bar: !!cfg.bar,
        steps: cfg.steps || 4,
        text: !!cfg.text,
        minWidth: cfg.minWidth || 80,
      });
      this.map.addControl(this._scaleLine);
    },

    // ===== Custom controls =====

    add_custom_control(spec) {
      if (this._customControls[spec.id]) return;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'nol-custom-button';
      if (spec.title) button.title = spec.title;
      button.innerHTML = spec.html || '';
      if (spec.active) button.classList.add('nol-custom-active');
      button.addEventListener('click', (e) => {
        e.stopPropagation();
        e.preventDefault();
        this.$emit('control_click', { id: spec.id });
      });

      const element = document.createElement('div');
      const position = spec.position || 'top-left';
      const stack = this._customControlCounts[position] || 0;
      this._customControlCounts[position] = stack + 1;
      element.className = `nol-custom-control nol-control-${position} ol-unselectable ol-control`;
      if (spec.classes) element.className += ' ' + spec.classes;
      // Default offsets clear the built-in OL controls in each corner:
      //   top-left:     under the zoom buttons
      //   top-right:    plain top, but right of any layer panel a user adds
      //   bottom-left:  clear of the scale-line
      //   bottom-right: above the attribution badge
      // Each additional control in the same corner stacks by ~2.2em.
      // Users can override with spec.css.
      const baseOffsetEm = position === 'top-left' ? 4.6
        : position === 'bottom-right' ? 2.5
        : 0.5;
      const offsetEm = `calc(${baseOffsetEm}em + ${stack * 2.2}em)`;
      const axis = position.startsWith('top') ? 'top' : 'bottom';
      element.style[axis] = offsetEm;
      if (spec.css) {
        for (const [k, v] of Object.entries(spec.css)) element.style[k] = v;
      }
      element.appendChild(button);

      const control = new ol.control.Control({ element });
      this.map.addControl(control);
      this._customControls[spec.id] = { control, spec, button };
    },

    remove_custom_control(id) {
      const entry = this._customControls[id];
      if (!entry) return;
      this.map.removeControl(entry.control);
      delete this._customControls[id];
      // do not decrement _customControlCounts: keeping the count stable
      // means later additions don't shift on top of existing buttons.
    },

    update_custom_control(id, patch) {
      const entry = this._customControls[id];
      if (!entry) return;
      const { button, spec } = entry;
      if ('html' in patch) {
        button.innerHTML = patch.html || '';
        spec.html = patch.html;
      }
      if ('title' in patch) {
        button.title = patch.title || '';
        spec.title = patch.title;
      }
      if ('active' in patch) {
        button.classList.toggle('nol-custom-active', !!patch.active);
        spec.active = !!patch.active;
      }
    },

    // ===== Measurement =====

    _ensureMeasureLayer() {
      if (this._measureLayer) return this._measureLayer;
      const styleFn = (feature) => this._measureFeatureStyle(feature);
      this._measureLayer = new ol.layer.Vector({
        source: new ol.source.Vector(),
        style: styleFn,
        zIndex: 1000,
      });
      this._measureLayer.set("nolId", "_measure");
      this.map.addLayer(this._measureLayer);
      return this._measureLayer;
    },

    _activateMeasure(kind) {
      const layer = this._ensureMeasureLayer();
      const opts = {
        source: layer.getSource(),
        type: "LineString",
        style: this._measureSketchStyle(),
      };
      if (kind === "Angle") opts.maxPoints = 3;
      this.drawInteraction = new ol.interaction.Draw(opts);
      this.drawInteraction.on("drawstart", (e) =>
        this._handleMeasureStart(e.feature, kind),
      );
      this.drawInteraction.on("drawend", (e) =>
        this._handleMeasureEnd(e.feature, kind),
      );
      this.map.addInteraction(this.drawInteraction);
    },

    _handleMeasureStart(feature, kind) {
      const geom = feature.getGeometry();
      const update = () => {
        const text = this._formatMeasure(geom, kind);
        this.measureTooltipText = text;
        this._measureTooltipOverlay.setPosition(geom.getLastCoordinate());
      };
      update();
      this._measureSketchListener = geom.on("change", update);
    },

    _handleMeasureEnd(feature, kind) {
      const geom = feature.getGeometry();
      const text = this._formatMeasure(geom, kind);
      this._measureCounter += 1;
      const id = `meas-${this._measureCounter}-${Date.now()}`;
      feature.setId(id);
      feature.set("nolFeatureId", id);
      feature.set("measureKind", kind);
      feature.set("measureText", text);
      if (!(this.measureConfig && this.measureConfig.persist !== false)) {
        // transient measurement: remove the feature once drawing finishes
        setTimeout(() => {
          const src = this._measureLayer && this._measureLayer.getSource();
          if (src && feature) src.removeFeature(feature);
        }, 0);
      }
      // hide live tooltip; the static label rendered by the feature style takes over
      this.measureTooltipText = "";
      this._measureTooltipOverlay.setPosition(undefined);
      const proj = this.currentProjection;
      const toLL = (c) => ol.proj.toLonLat(c, proj);
      const coords = geom.getCoordinates().map(toLL);
      this.$emit("measure", {
        kind,
        feature_id: id,
        text,
        value: this._measureValue(geom, kind),
        coords,
        units: this._measureUnitsFor(kind),
        bearing: kind === "Distance" ? this._currentBearing(geom) : null,
      });
      // pop out of the tool unless the user wants continuous measuring
      if (!(this.measureConfig && this.measureConfig.continuous)) {
        setTimeout(() => this.setMode(null), 0);
      }
    },

    clearMeasurements() {
      if (!this._measureLayer) return;
      this._measureLayer.getSource().clear();
      this.measureTooltipText = "";
      if (this._measureTooltipOverlay) this._measureTooltipOverlay.setPosition(undefined);
    },

    _measureSketchStyle() {
      const { Style, Stroke, Fill, Circle: CircleStyle } = ol.style;
      return new Style({
        stroke: new Stroke({ color: "#f97316", width: 2, lineDash: [6, 4] }),
        image: new CircleStyle({
          radius: 5,
          fill: new Fill({ color: "#f97316" }),
          stroke: new Stroke({ color: "#fff", width: 2 }),
        }),
      });
    },

    _measureFeatureStyle(feature) {
      const { Style, Stroke, Fill, Circle: CircleStyle, Text } = ol.style;
      const text = feature.get("measureText") || "";
      const styles = [
        new Style({
          stroke: new Stroke({ color: "#f97316", width: 3 }),
        }),
      ];
      // small dot at each vertex
      const geom = feature.getGeometry();
      if (geom && geom.getType() === "LineString") {
        for (const c of geom.getCoordinates()) {
          styles.push(new Style({
            geometry: new ol.geom.Point(c),
            image: new CircleStyle({
              radius: 4,
              fill: new Fill({ color: "#fff" }),
              stroke: new Stroke({ color: "#f97316", width: 2 }),
            }),
          }));
        }
      }
      if (text && geom) {
        const labelCoord = feature.get("measureKind") === "Angle"
          ? geom.getCoordinates()[1] || geom.getLastCoordinate()
          : geom.getLastCoordinate();
        styles.push(new Style({
          geometry: new ol.geom.Point(labelCoord),
          text: new Text({
            text,
            font: "bold 12px sans-serif",
            offsetY: -14,
            padding: [3, 6, 3, 6],
            fill: new Fill({ color: "#0f172a" }),
            stroke: new Stroke({ color: "#fff", width: 4 }),
            backgroundFill: new Fill({ color: "rgba(255, 247, 237, 0.95)" }),
            backgroundStroke: new Stroke({ color: "#f97316", width: 1 }),
          }),
        }));
      }
      return styles;
    },

    _formatMeasure(geom, kind) {
      if (kind === "Angle") {
        const ang = this._geodesicAngle(geom);
        return ang == null ? "—" : ang.toFixed(1) + "°";
      }
      const lenText = this._formatLength(this._geodesicLength(geom));
      const bearing = this._currentBearing(geom);
      if (bearing == null) return lenText;
      return `${lenText}  ${bearing.toFixed(0).padStart(3, "0")}°`;
    },

    _measureValue(geom, kind) {
      if (kind === "Angle") return this._geodesicAngle(geom);
      return this._geodesicLength(geom);
    },

    _measureUnitsFor(kind) {
      if (kind === "Angle") return "degrees";
      return (this.measureConfig && this.measureConfig.units) || "metric";
    },

    _geodesicLength(geom) {
      // ol.sphere.getLength reprojects from the view projection to the WGS84
      // sphere internally and returns a length in metres.
      return ol.sphere.getLength(geom, { projection: this.currentProjection });
    },

    _currentBearing(geom) {
      // Bearing of the most recent segment (last-but-one coordinate -> last).
      const coords = geom.getCoordinates();
      if (!coords || coords.length < 2) return null;
      const proj = this.currentProjection;
      const a = ol.proj.toLonLat(coords[coords.length - 2], proj);
      const b = ol.proj.toLonLat(coords[coords.length - 1], proj);
      if (a[0] === b[0] && a[1] === b[1]) return null;
      return this._initialBearing(a, b);
    },

    _geodesicAngle(geom) {
      const coords = geom.getCoordinates();
      if (coords.length < 3) return null;
      const proj = this.currentProjection;
      const toLL = (c) => ol.proj.toLonLat(c, proj);
      const a = toLL(coords[0]);
      const b = toLL(coords[1]);
      const c = toLL(coords[2]);
      const br1 = this._initialBearing(b, a);
      const br2 = this._initialBearing(b, c);
      let diff = Math.abs(br1 - br2);
      if (diff > 180) diff = 360 - diff;
      return diff;
    },

    _initialBearing(from, to) {
      const φ1 = (from[1] * Math.PI) / 180;
      const φ2 = (to[1] * Math.PI) / 180;
      const dλ = ((to[0] - from[0]) * Math.PI) / 180;
      const y = Math.sin(dλ) * Math.cos(φ2);
      const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(dλ);
      return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
    },

    _formatLength(metres) {
      const u = (this.measureConfig && this.measureConfig.units) || "metric";
      if (u === "imperial" || u === "us") {
        const ft = metres * 3.28084;
        if (ft > 5280) return (ft / 5280).toFixed(2) + " mi";
        return ft.toFixed(0) + " ft";
      }
      if (u === "nautical") {
        const nm = metres / 1852;
        return nm.toFixed(nm < 1 ? 3 : 2) + " nmi";
      }
      if (metres > 1000) return (metres / 1000).toFixed(2) + " km";
      return metres.toFixed(metres < 10 ? 2 : 1) + " m";
    },

    measureLabel(t) {
      return {
        Distance: "Measure distance",
        Angle: "Measure angle (3 clicks)",
      }[t] || t;
    },

    measureIcon(t) {
      const stroke = "currentColor";
      if (t === "Distance") {
        return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17 L17 3 L21 7 L7 21 Z"/><path d="M7 13 L9 15 M11 9 L13 11 M15 5 L17 7"/></svg>`;
      }
      if (t === "Angle") {
        return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20 L20 20"/><path d="M4 20 L18 6"/><path d="M9 20 A5 5 0 0 0 12 15.5"/></svg>`;
      }
      return "?";
    },

    set_measure_config(cfg) {
      this.measureConfig = { ...this.measureConfig, ...cfg };
    },

    _activateDraw(layer, mode) {
      const olDrawType = mode === "Rectangle" ? "Circle" : mode;
      const opts = {
        source: layer.getSource(),
        type: olDrawType,
        style: this._drawSketchStyle(),
      };
      if (mode === "Rectangle" && ol.interaction.Draw.createBox) {
        opts.geometryFunction = ol.interaction.Draw.createBox();
      }
      this.drawInteraction = new ol.interaction.Draw(opts);
      this.drawInteraction.on("drawend", (e) => this._handleDrawEnd(e, mode, layer));
      this.map.addInteraction(this.drawInteraction);
      if (this.drawConfig.snap) {
        this.snapInteraction = new ol.interaction.Snap({ source: layer.getSource() });
        this.map.addInteraction(this.snapInteraction);
      }
    },

    _activateModify(layer) {
      this.modifyInteraction = new ol.interaction.Modify({ source: layer.getSource() });
      this.modifyInteraction.on("modifyend", (e) => this._handleModifyEnd(e, layer));
      this.map.addInteraction(this.modifyInteraction);
      if (this.drawConfig.snap) {
        this.snapInteraction = new ol.interaction.Snap({ source: layer.getSource() });
        this.map.addInteraction(this.snapInteraction);
      }
    },

    _activateDelete(layer) {
      const layerId = layer.get("nolId");
      this._deleteClickKey = this.map.on("singleclick", (evt) => {
        const hits = [];
        this.map.forEachFeatureAtPixel(
          evt.pixel,
          (feat, lyr) => { if (lyr === layer) hits.push(feat); },
          { layerFilter: (lyr) => lyr === layer, hitTolerance: 4 },
        );
        if (!hits.length) return;
        for (const feat of hits) {
          const id = feat.get("nolFeatureId");
          if (!id) continue;
          layer.getSource().removeFeature(feat);
          delete this.olFeatures[layerId][id];
          delete this.featureSpecs[layerId][id];
          this.$emit("draw_deleted", { layer_id: layerId, feature_id: id });
        }
        this.closePopup();
      });
    },

    _drawSketchStyle() {
      const { Style, Stroke, Fill, Circle: CircleStyle } = ol.style;
      return new Style({
        stroke: new Stroke({ color: "#2563eb", width: 2, lineDash: [6, 4] }),
        fill: new Fill({ color: "rgba(37, 99, 235, 0.15)" }),
        image: new CircleStyle({
          radius: 6,
          fill: new Fill({ color: "#2563eb" }),
          stroke: new Stroke({ color: "#fff", width: 2 }),
        }),
      });
    },

    _drawnFeatureStyle(spec) {
      // built off our _buildStyle so drawn features look like our normal ones
      return this._buildStyle(spec);
    },

    _highlightStyle() {
      const { Style, Stroke, Fill, Circle: CircleStyle } = ol.style;
      return new Style({
        stroke: new Stroke({ color: "#dc2626", width: 3 }),
        fill: new Fill({ color: "rgba(220, 38, 38, 0.2)" }),
        image: new CircleStyle({
          radius: 7,
          fill: new Fill({ color: "#dc2626" }),
          stroke: new Stroke({ color: "#fff", width: 2 }),
        }),
      });
    },

    _handleDrawEnd(e, mode, layer) {
      const feature = e.feature;
      const layerId = layer.get("nolId");
      this._drawCounter += 1;
      const featureId = `draw-${this._drawCounter}-${Date.now()}`;
      const spec = this._featureSpecFromGeometry(feature.getGeometry(), mode);
      feature.setId(featureId);
      feature.set("nolFeatureId", featureId);
      feature.set("nolLayerId", layerId);
      feature.setStyle(this._drawnFeatureStyle(spec));
      this.olFeatures[layerId][featureId] = feature;
      this.featureSpecs[layerId][featureId] = spec;
      this.$emit("draw_created", {
        layer_id: layerId,
        feature_id: featureId,
        type: spec.type,
        coords: spec.coords,
      });
      if (!this.drawConfig.continuous) {
        // pop out of draw mode after one shape
        setTimeout(() => this.setMode(null), 0);
      }
    },

    _handleModifyEnd(e, layer) {
      const layerId = layer.get("nolId");
      e.features.forEach((feature) => {
        const id = feature.get("nolFeatureId");
        if (!id) return;
        const oldSpec = this.featureSpecs[layerId]?.[id] || {};
        const spec = this._featureSpecFromGeometry(feature.getGeometry(), oldSpec.shape || oldSpec._mode);
        const merged = { ...oldSpec, coords: spec.coords };
        this.featureSpecs[layerId][id] = merged;
        this.$emit("draw_modified", {
          layer_id: layerId,
          feature_id: id,
          coords: spec.coords,
        });
      });
    },

    _featureSpecFromGeometry(geom, mode) {
      const t = geom.getType();
      const proj = this.currentProjection;
      const toLL = (c) => ol.proj.toLonLat(c, proj);
      if (t === "Point") {
        return { type: "marker", shape: "Point", coords: toLL(geom.getCoordinates()) };
      }
      if (t === "LineString") {
        return { type: "line", shape: "LineString",
                 coords: geom.getCoordinates().map(toLL) };
      }
      if (t === "Polygon") {
        return { type: "polygon",
                 shape: mode === "Rectangle" ? "Rectangle" : "Polygon",
                 coords: geom.getCoordinates().map((ring) => ring.map(toLL)) };
      }
      return { type: "unknown", shape: t };
    },

    clearDrawLayer() {
      const layerId = this.drawConfig.layerId;
      if (!layerId) return;
      const ids = Object.keys(this.olFeatures[layerId] || {});
      this.clear_layer(layerId);
      for (const id of ids) {
        this.$emit("draw_deleted", { layer_id: layerId, feature_id: id });
      }
    },

    toolLabel(t) {
      return {
        Point: "Draw point",
        LineString: "Draw line",
        Polygon: "Draw polygon",
        Rectangle: "Draw rectangle",
        Edit: "Edit",
        Delete: "Delete",
        Clear: "Clear",
      }[t] || t;
    },

    toolIcon(t) {
      const stroke = "currentColor";
      switch (t) {
        case "Point":
          return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4" fill="${stroke}"/></svg>`;
        case "LineString":
          return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18 L10 8 L14 14 L20 5"/><circle cx="4" cy="18" r="1.6" fill="${stroke}"/><circle cx="10" cy="8" r="1.6" fill="${stroke}"/><circle cx="14" cy="14" r="1.6" fill="${stroke}"/><circle cx="20" cy="5" r="1.6" fill="${stroke}"/></svg>`;
        case "Polygon":
          return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 7 L17 4 L20 14 L12 20 L4 14 Z"/></svg>`;
        case "Rectangle":
          return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2"><rect x="4" y="6" width="16" height="12"/></svg>`;
        case "Edit":
          return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4 L20 10 L9 21 L3 21 L3 15 Z"/></svg>`;
        case "Delete":
          return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7 H20 M9 7 V4 H15 V7 M6 7 L7 21 H17 L18 7"/></svg>`;
        case "Clear":
          return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 5 L19 19 M19 5 L5 19"/></svg>`;
        default:
          return "?";
      }
    },

    // ===== Click handling =====

    handleClick(evt) {
      const suppressPopup = this.activeMode === "Delete";
      let popupShown = false;
      const features = this.map.getFeaturesAtPixel(evt.pixel) || [];
      for (const feature of features) {
        const featureId = feature.get("nolFeatureId");
        const layerId = feature.get("nolLayerId");
        const popup = feature.get("nolPopup");
        const geom = feature.getGeometry();
        const coord = geom.getType() === "Point"
          ? geom.getCoordinates()
          : evt.coordinate;
        if (!suppressPopup && popup && !popupShown) {
          this.popupHtml = popup;
          this.popupVisible = true;
          this.popupOverlay.setPosition(coord);
          popupShown = true;
        }
        this.$emit("feature_click", {
          layer_id: layerId,
          feature_id: featureId,
          coord: ol.proj.toLonLat(evt.coordinate, this.currentProjection),
        });
      }
      if (!features.length && !suppressPopup) {
        this.closePopup();
      }
      this.$emit("map_click", { coord: ol.proj.toLonLat(evt.coordinate, this.currentProjection) });
    },
  },
};
