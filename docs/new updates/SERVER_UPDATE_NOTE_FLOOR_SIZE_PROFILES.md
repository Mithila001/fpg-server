# Server Update Note — Dynamic Floor-Size Preprocessing

**Date:** 2026-08-16  
**Scope:** `fpg-server` preprocessing configuration and generation metadata

## Purpose

This update improves how the server handles floor-plan size during preprocessing. Instead of using one fixed hallway/circulation allowance and one global hallway-count limit for every floor size, the server now resolves a floor-size profile for each generation request.

The same rules are also exposed through the existing metadata API so the client can perform matching UI/UX validation before starting generation.

## Updated Behavior

### 1. Floor-size profiles

Three floor-size categories were introduced:

| Category | Floor area | Circulation ratio | Max hallway count |
|---|---:|---:|---:|
| `small` | ≤ 80 m² | 7% | 2 |
| `medium` | > 80 m² and ≤ 150 m² | 9% | 4 |
| `large` | > 150 m² | 11% | 5 |

In project units, where `10 units = 1 meter`, the thresholds are:

- `small`: `max_floor_area = 8000`
- `medium`: `max_floor_area = 15000`
- `large`: no upper limit

### 2. Dynamic circulation allowance

The previous fixed preprocessing value:

```json
"hallway_area_buffer": 300.0
```

was replaced by:

```json
"minimum_circulation_area": 300.0
```

plus the circulation ratio defined by the selected floor-size profile.

The server calculates:

```text
circulation allowance = max(
    minimum circulation area,
    ceil(floor area × profile circulation ratio)
)
```

The minimum remains `300` square project units, equivalent to approximately `3 m²`.

Decimal-based ceiling calculation is used to avoid floating-point rounding errors at exact boundaries.

### 3. Dynamic maximum hallway count

`max_hallway_room_count` is no longer one global value.

The value passed to `fpg-core` preprocessing is selected from the active floor-size profile:

- Small floor → maximum 2 hallway rooms
- Medium floor → maximum 4 hallway rooms
- Large floor → maximum 5 hallway rooms

### 4. Per-request preprocessing configuration

A new floor-size policy is loaded as part of `ServerConfig`.

Before calling `fpg_core.floor_plan_preprocessing.prepare_generation_input()`, the generation pipeline now:

1. Calculates the requested floor-limit area from `max_width × max_length`.
2. Resolves the matching floor-size profile.
3. Creates a request-specific `PreprocessingConfig`.
4. Overrides the core preprocessing values for:
   - `hallway_area_buffer`
   - `max_hallway_room_count`
5. Passes that resolved configuration to `fpg-core`.

This keeps `fpg-core` usage compatible while allowing the server to apply dynamic policy per request.

### 5. Preprocessing progress information

The preprocessing stage now includes the resolved floor policy information in its progress/log data:

- `floor_size_category`
- `floor_limit_area`
- `circulation_ratio`
- `circulation_allowance_area`
- `max_hallway_room_count`

This makes it easier to understand which policy was applied to a generation request.

### 6. Hallway width consistency

The hallway-dimension scoring/configuration minimum was changed from:

```text
8 units = 0.8 m
```

to:

```text
10 units = 1.0 m
```

This now matches the preprocessing `hallway_min_width` value of `10` units.

## Metadata API Update

No new endpoint was added. The existing:

```text
GET /api/v1/metadata
```

was extended with `floor_plan_constraints`.

The client can now receive:

- minimum floor width
- minimum floor length
- minimum floor area
- source of the land-specific maximum floor dimensions
- floor-area buffer
- hallway minimum width
- minimum circulation area
- circulation calculation mode
- circulation rounding rule
- floor-size profile thresholds
- circulation ratios
- maximum hallway counts

The land-specific maximum floor size is still obtained from:

```text
POST /api/v1/buildable-space
```

rather than defining one global maximum in metadata.

## Example — 10 m × 10 m Floor

A `10 m × 10 m` floor is represented as:

```text
100 × 100 units = 10,000 square project units = 100 m²
```

It resolves to the `medium` profile:

```text
Circulation allowance = 10,000 × 0.09 = 900 units² ≈ 9 m²
Maximum hallway count = 4
```

## Files Updated

- `app/core_config.py`
  - Added floor-size profile/policy models and validation.
  - Added per-floor preprocessing configuration resolution.

- `app/data/server_config.json`
  - Replaced fixed hallway-area/count settings with floor-size profiles.
  - Aligned hallway minimum scoring width to 10 units.

- `app/pipeline/generation/pipeline.py`
  - Resolves the floor-size profile before preprocessing.
  - Passes request-specific preprocessing configuration to `fpg-core`.
  - Adds resolved policy values to preprocessing progress data.

- `app/routes/generation.py`
  - Extended `/api/v1/metadata` with floor-plan constraint and circulation policy metadata.

## Compatibility Notes

- The generation API request structure was not changed.
- No new API endpoint is required.
- `fpg-core` itself was not modified by this server update.
- The server remains authoritative for preprocessing validation; metadata is exposed so the client can reproduce the relevant checks for UI/UX feedback.
