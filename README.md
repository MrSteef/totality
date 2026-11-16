# Eclipse 2027 — location-specific totality map

Static website; no API key or server-side computation required. Every hover and click evaluates the **NASA Besselian elements at that exact coordinate** using the local C2/C3 contact equations. Background colored raster is pre-generated from those same calculations; it is **not** merely a colorized centerline.

## Run

```bash
python -m http.server 8000
# Open http://localhost:8000
```

Map tiles and MapLibre JS load from external public CDNs; internet is needed when viewing. Deploy the folder to GitHub Pages, Netlify, or Vercel.

## Regenerate overlay

```bash
pip install numpy pillow
python build_overlay.py
```

The generated `data/duration.png` is already included. Raster geographic bounds: west -52°, east 68°, south -8°, north 45°. The image is 2160 × 1053 pixels, sampled at pixel centers in **Web Mercator** coordinates (not linearly in latitude). This is critical for accurate alignment in MapLibre image sources. Raster colors are **visual approximation**; hovering or clicking uses continuous numerical calculation, independent of pixel resolution.

## Scientific basis and limitations

- NASA/Espenak Besselian elements: https://eclipse.gsfc.nasa.gov/SEbeselm/SEbeselm2001/SE2027Aug02Tbeselm.html
- Eclipse path reference: https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2027Aug02Tpath.html
- ΔT 71.7 sec, ellipsoidal Earth approximation and smooth lunar edge (no lunar-limb profile corrections).
- C2/C3 are calculated via root finding for the local umbral contact equation. Each location's duration is computed separately, and goes to zero near the corridor edge.
- Times are displayed in UTC, rounded to nearest second, and are predictions, not confirmed observational times.
- Published NASA eclipse greatest duration 6m23.2s; near-center calculated max should be ~383 sec.
- **Not yet validated** against a full set of independent locality observations, precision geographic path boundaries, or lunar-limb topography. Check individual candidate destinations with NASA / Timeanddate before making travel commitments.
- Not guaranteed solar visibility: cloud, terrain, travel accessibility, precise viewing point and weather matter. The color raster is not suitable for identifying the exact boundary; use the live calculation and independent references.

## Coordinates and tech

MapLibre GL JS + OpenFreeMap tiles; `eclipse.mjs` is plain ES module JavaScript; `build_overlay.py` creates the RGBA heatmap. No external eclipse API required.

## Overlay alignment fix (v2)

The previous raster sampled image rows at uniform latitude intervals, while MapLibre maps image pixels uniformly in Web Mercator *projected* Y coordinates. This moved the rendered band several degrees north, incorrectly showing it near Cairo while exact-coordinate clicks at Luxor remained correct. The new Python generator samples rows in Mercator space, and the map uses matching corners. The generator asserts Luxor is opaque and Cairo is transparent. The PNG is more than twice as wide and has higher resolution.

If you have an older version cached in your browser, hard-refresh the page; the new source URL uses `duration.png?v=2` for cache busting.

## Critical correction (v3 — November 2026)

Previous releases omitted the Earth-rotation correction for the TT−UT difference in the Besselian hour angle μ. This displaced the entire computed path by roughly 30 km and badly distorted durations near its edge. Both `eclipse.mjs` and `build_overlay.py` now evaluate:

```
H = (mu(TT) + longitudeEast - 15.002093 * 71.7 / 3600) * pi / 180
```

The longitude is east-positive. The table's x/y/d/l2 polynomials continue to use TT. Regenerate the image whenever changing the eclipse model; keep the JavaScript and Python copies in sync.

Approximate cross-checks using coordinate-defined points (rounded to seconds):

| Location and input coordinate | Updated model | Timeanddate reference |
|---|---:|---:|
| Sana, 15.3500°N 44.2167°E | 2m 20s | 2m 28s |
| Luxor, 25.6872°N 32.6396°E | 6m 20s | 6m 22s |
| Jeddah, 21.5433°N 39.1728°E | 5m 56s | 5m 55s |
| Tarifa, 36.0130°N -5.6050°E | 4m 39s | ~4m 40s |

These aren't necessarily identical observation coordinates to the reference site; near a path boundary, small location differences can change the reported duration materially. For trip planning, independently verify your exact lodging/viewing coordinates, especially within tens of km of the boundary.

Run `node test.mjs` before publishing. The tests also cover NASA's duration maximum and two tabulated corridor edge coordinates.

## New: independent August cloud-cover layer (v4)

The two top-left checkboxes independently show/hide **Totality duration** and **Historical August cloud cover**. Both may be visible simultaneously. When cloud data has been generated, clicking/hovering also shows historical cloud-cover percentages (not forecasts).

### One-time data generation (internet required)

This package intentionally does **not** contain fabricated cloud data. The NASA POWER data service wasn't reachable from the build environment, so you must retrieve the real data once before deploying:

```bash
python -m pip install numpy pillow requests scipy
python build_cloud.py
python -m http.server 8000
```

The generator requests regional NASA POWER climatology (`CLOUD_AMT_DAY` — daytime cloud fraction, **August 2005–2024**) in 10-degree tiles, and writes `data/cloud-august.png` and `data/cloud-grid.json`. The browser detects these files automatically. **If absent, the cloud toggle is visibly disabled**, rather than displaying invented results. Deploy both generated files alongside the website. The existing `data/duration.png` is unchanged.

NASA POWER climatology API: https://power.larc.nasa.gov/docs/services/api/temporal/climatology/
NASA CERES cloud methodology: https://power.larc.nasa.gov/docs/methodology/data/sources_clds_aerosols/

This layer displays an August daytime **mean cloud fraction**, not a probability of a cloud-free eclipse, and not a forecast. The native source resolution is approximately 1 degree; visual smoothing adds no geographic precision. Local terrain, coastal fog, time of day, and year-to-year variability can all make an actual site quite different. For travel decisions, also consult historical cloud cover around the local eclipse hour, ideally using multi-year hourly records, and revisit short-range weather forecasts closer to August 2, 2027.
