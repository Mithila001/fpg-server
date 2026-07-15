# Legacy Candidate Scoring — Behavioural Analysis

## Document purpose

This document records the behaviour and apparent intent of the legacy `fpg_optuna_score` package before that package is replaced.

The purpose is not to preserve the legacy code structure. It is to recover the scoring concepts that the code was trying to implement so the project can later:

1. decide which concepts remain valid,
2. correct weak or accidental behaviour,
3. design a new scoring system from first principles, and
4. remove the legacy files without losing domain knowledge.

This document separates three things wherever possible:

- **Implemented behaviour** — what the legacy code actually calculates.
- **Intended scoring behaviour** — the architectural quality the calculation appears to approximate.
- **Review findings** — weaknesses, ambiguities, and behaviour that should not be copied automatically.

---

# 1. Scope of the legacy scorer

The legacy scorer evaluates a set of sampled room centre-like points produced during candidate search.

It does **not** evaluate a completed floor plan. At this stage there are no confirmed:

- room polygons,
- room dimensions,
- shared walls,
- doors,
- windows,
- non-overlap guarantees,
- real circulation routes,
- final exterior boundaries around individual rooms.

The scorer therefore estimates whether a point arrangement is a promising spatial hint for a later generation stage.

Its practical responsibility is:

> Assign a scalar quality score to one sampled arrangement of room points and decide whether that candidate reaches a configured gate threshold.

The legacy package divides that responsibility into four sections:

1. floor-plan zones,
2. outer clearance,
3. room relations,
4. spatial coverage.

The manager sums their section scores and compares the total against a configured threshold.

---

# 2. Legacy input preparation

## 2.1 Inputs received by the manager

The public function receives:

- an `FpgRequirements` object,
- a mapping of sampled positions,
- an unused or externally intended `save_debug_plots` flag.

The sampled-position mapping may contain positions in several formats:

- `{ "x": ..., "y": ... }`,
- `{ "position": ... }`, recursively containing a supported format,
- a sequence whose first two values are interpreted as `x` and `y`.

Values that cannot be converted to two floats are treated as missing.

## 2.2 Construction of scoring points

For every room in `requirements.rooms`, the code looks up a sampled position by the room's **name**.

A valid entry becomes:

```text
OptunaScorePoint
    name
    room_type
    x
    y
```

If a required room has no usable sampled position, the code logs the issue and silently excludes that room from scoring.

After processing declared rooms, the code includes extra sampled nodes when:

- the sampled value explicitly contains a `type`, or
- the sampled key begins with `hallway`, in which case the room type is inferred as hallway.

Unknown extra points without a type are ignored.

## Intended behaviour

The scorer needs a unified point representation for both requested rooms and dynamically generated candidate nodes such as hallways.

## Review findings

The intended need is valid, but the legacy implementation is fragile:

- room names act as identifiers,
- missing declared rooms are silently removed rather than making the candidate invalid,
- hallway identity may be inferred from text naming,
- unknown extra nodes disappear silently,
- no validation confirms unique names,
- no validation confirms finite coordinates,
- no validation confirms that coordinates are inside the floor,
- no distinction exists between required, optional, and generated nodes.

These behaviours should be considered legacy input tolerance, not part of the desired scoring logic.

---

# 3. Shared section-score behaviour

Every evaluator returns a `SectionScore` containing:

- `score`,
- `max_score`,
- an arbitrary details dictionary,
- a list of warning strings.

A shared normalization helper clamps a raw section score to:

```text
0 <= score <= max_score
```

If `max_score <= 0`, it returns zero.

## Intended behaviour

Each scoring concern contributes a bounded amount to the total candidate score, while diagnostics explain how the score was produced.

## Review findings

The concept is valid, but the legacy contract is weak:

- evaluator detail structures are unrelated and untyped,
- status such as “not applicable” is represented inconsistently,
- some missing-applicability cases receive full score,
- section weights are fetched globally from configuration,
- some internal component maxima are fixed independently of the configured section maximum.

---

# 4. Floor-plan zone scoring

## 4.1 Architectural quality being approximated

This evaluator tries to encourage important room categories toward broad regions of the floor where they are more likely to be architecturally appropriate.

The apparent orientation assumption is:

```text
Higher Y
Back of floor

+---------+---------+---------+
|  (1,3)  |  (2,3)  |  (3,3)  |
+---------+---------+---------+
|  (1,2)  |  (2,2)  |  (3,2)  |
+---------+---------+---------+
|  (1,1)  |  (2,1)  |  (3,1)  |
+---------+---------+---------+
Front of floor
Lower Y
```

The floor is normalized and divided into a conceptual 3 × 3 grid.

## 4.2 Room types evaluated

Only these room types are zone-scored:

- veranda,
- garage,
- kitchen,
- hallway,
- living room,
- bathroom.

Bedrooms, dining rooms, attached bathrooms, and unknown types do not contribute to this section.

## 4.3 Preferred zones

### Veranda

Valid anywhere in the front row:

```text
(1,1), (2,1), (3,1)
```

**Apparent intent:** place the veranda toward the front facade.

### Garage

Valid in the front-left or front-right corner:

```text
(1,1), (3,1)
```

**Apparent intent:** place the garage against a front-side edge rather than centrally.

### Kitchen

Valid everywhere except the centre cell:

```text
all cells except (2,2)
```

**Apparent intent:** avoid burying the kitchen at the centre, likely to preserve exterior access, ventilation, or service access.

### Hallway

Valid in the middle and back rows:

```text
all cells except the front row
```

**Apparent intent:** prevent circulation space from occupying valuable front-facing space.

### Living room

Valid in the front and middle rows:

```text
all cells where Y-cell is 1 or 2
```

**Apparent intent:** keep the living room accessible from the front/public side and avoid pushing it deep into the back.

### Bathroom

Valid everywhere except the centre cell:

```text
all cells except (2,2)
```

**Apparent intent:** avoid a centrally enclosed bathroom, likely due to ventilation, privacy, or circulation concerns.

## 4.4 Exact implemented calculation

For each scorable room:

1. Normalize its point:

```text
nx = x / floor_width
ny = y / floor_height
```

If a floor dimension is non-positive, that normalized coordinate defaults to `0.5`.

2. Convert every valid 3 × 3 cell into a normalized rectangular region.

3. Measure the shortest Euclidean distance from the point to the boundary of any valid region.

- A point inside a valid region has distance `0`.
- A point outside all valid regions has a positive normalized distance.

4. Convert distance to a room score:

```text
room_score_100 = max(0, 100 × (1 - distance × 1.5))
```

Therefore:

- inside a valid region → `100`,
- increasingly outside the valid region → linear score reduction,
- distance of approximately `0.6667` or more → `0`.

5. Average all scorable room scores.

6. Scale that average onto the configured zone-section maximum.

Equivalent formula:

```text
zone_ratio = sum(room_score_100) / (number_of_scorable_rooms × 100)
zone_score = zone_ratio × configured_zone_max
```

7. Clamp the result between zero and the configured section maximum.

## 4.5 Missing-applicability behaviour

If no zone-scorable rooms exist, the evaluator awards the full configured zone score and emits a warning.

## 4.6 Diagnostics produced

For every scored room, the evaluator records:

- room type,
- discrete 3 × 3 cell,
- normalized position,
- shortest distance to an allowed region,
- score out of 100,
- textual reason,
- approximate contribution to the final section score.

It also records room-type counts and the number of scorable rooms.

## 4.7 Intended scoring behaviour

The intended concept appears to be:

> Encourage selected room types toward broad preferred floor regions, while using a soft distance-based penalty rather than rejecting a candidate immediately when a point falls outside a preferred zone.

This is a candidate-guidance preference, not a geometric constraint.

## 4.8 Review findings

### Valid ideas

- broad region preferences are appropriate for early candidate search,
- normalized coordinates make the rule independent of absolute floor size,
- continuous falloff is better than a hard cell boundary,
- averaging prevents layouts with more scorable rooms from automatically receiving larger scores.

### Unclear or weak assumptions

- the front direction is hard-coded as lower Y,
- the same rules apply to every project configuration,
- room-specific requirements are ignored,
- all instances of a room type receive equal influence,
- bedroom and dining placement have no zone preference,
- the preferred regions are coarse and manually fixed,
- kitchen and bathroom share the same “not centre” rule despite different architectural reasons,
- no distinction exists between common and attached bathrooms,
- invalid floor dimensions are hidden by substituting `0.5` rather than failing validation.

### Behaviour that should not be copied automatically

- awarding full section score when there are no applicable rooms,
- treating a room missing from the point set as if it never existed,
- relying on legacy string room types,
- storing room diagnostics keyed by potentially non-unique room names.

---

# 5. Outer-clearance scoring

## 5.1 Architectural quality being approximated

This evaluator tries to reserve unobstructed point-space in front of rooms that need exterior approach or access, and behind rooms that may provide a rear exit.

It evaluates three independent concepts:

1. veranda front clearance,
2. garage front clearance,
3. availability of a rear opening through a kitchen or hallway.

Despite its name, it does not calculate actual clearance to the outer floor boundary. It checks whether other sampled room points fall inside directional rectangles around selected room points.

## 5.2 Directional clearance rectangles

Given room point `(x, y)`, the evaluator defines fixed rectangles:

### Front

```text
x from x - 10 to x + 10
y from y - 20 to y
```

### Back

```text
x from x - 10 to x + 10
y from y to y + 20
```

### Left

```text
x from x - 20 to x
y from y - 10 to y + 10
```

### Right

```text
x from x to x + 20
y from y - 10 to y + 10
```

Only front and back are used by the public evaluator.

A blocker is any other room point inside or on the rectangle boundary.

The rectangle is not clipped to the floor boundary.

## 5.3 Blocker penalty

Each blocker reduces the component score by 10 percentage points:

```text
score = max(0, base_score - 10 × blocker_count)
```

## 5.4 Veranda component

For every veranda:

- evaluate its front rectangle,
- begin at 100,
- subtract 10 per blocking room point,
- clamp at zero.

If multiple verandas exist, average their scores.

If no veranda exists, this component is marked as not evaluated.

### Apparent intent

A veranda should have a clear approach or open frontage and should not be spatially blocked by other candidate rooms.

## 5.5 Garage component

For every garage:

- evaluate its front rectangle,
- begin at 100,
- subtract 10 per blocking room point,
- clamp at zero.

If multiple garages exist, average their scores.

If no garage exists, this component is marked as not evaluated.

### Apparent intent

A garage should retain an unobstructed vehicle approach from the front side.

## 5.6 Rear-opening component

The evaluator searches for the best rear-clearance option among:

- all kitchens, each with base score `100`,
- all hallways, each with base score `70`.

For each candidate room:

- evaluate its back rectangle,
- subtract 10 per blocker,
- clamp at zero.

The component receives only the highest score found across all kitchens and hallways.

If neither kitchens nor hallways exist, the component is not evaluated.

### Apparent intent

The floor plan should provide at least one practical rear-access location. A kitchen is the preferred source of that access; a hallway is an acceptable but weaker alternative.

## 5.7 Section aggregation

The evaluator runs the three components and includes only components that were evaluated.

```text
clearance_percentage = sum(applicable_component_scores) / applicable_component_count
clearance_score = clearance_percentage / 100 × configured_clearance_max
```

The result is clamped to the configured section maximum.

If no component is applicable, the evaluator awards the full configured section score.

## 5.8 Diagnostics produced

The normal result records only:

- number of evaluated components,
- average percentage achieved.

It does not expose:

- which rooms were evaluated,
- blocker names,
- component-level scores,
- which kitchen or hallway won the rear-opening check.

## 5.9 Intended scoring behaviour

The intended concept appears to be:

> Preserve likely exterior-access corridors around selected candidate rooms, especially veranda frontage, garage approach, and at least one rear exit location.

This is an early spatial-clearance heuristic. It cannot confirm real exterior access because room extents and final floor geometry are not yet known.

## 5.10 Review findings

### Valid ideas

- external-access needs should influence early candidate placement,
- unavailable optional room categories should not automatically reduce the score,
- using the best rear-opening candidate matches the requirement that at least one rear access route may be sufficient,
- garage, veranda, and rear-door needs are meaningfully different concerns.

### Unclear or weak assumptions

- clearance dimensions `20 × 20` are absolute constants and do not scale with floor size or room size,
- the coordinate orientation is assumed globally,
- point inclusion is used as a proxy for room-shape obstruction,
- every blocking point has identical severity,
- near-boundary placement is not checked,
- a clearance rectangle can extend outside the floor and still count as clear,
- kitchen is always preferred over hallway through fixed base scores,
- only front and back access are considered,
- multiple required exterior openings are not represented.

### Potential scoring distortion

The three applicable components have equal influence regardless of project needs. For example:

- veranda frontage,
- garage vehicle access,
- rear emergency/service exit

all receive one-third of the section when all are present.

A project with multiple verandas first averages all verandas into one component, while a single garage still occupies an equal component share.

### Behaviour that should not be copied automatically

- full score when nothing is applicable,
- fixed clearance dimensions embedded in code,
- no detailed component result,
- silent treatment of missing expected points,
- naming the evaluator “outer clearance” when it does not verify the outer boundary.

---

# 6. Room-relations scoring

## 6.1 Architectural quality being approximated

This evaluator tries to estimate:

- whether functionally related room categories are spatially close,
- whether important origin-to-destination routes are short,
- whether indirect paths avoid severe directional reversals,
- whether hallways tend to specialize toward public or private circulation rather than mixing both heavily.

It represents candidate points as nodes in an undirected graph and evaluates shortest paths over selected relation edges.

This is not a graph of confirmed doors or traversable space. It is a conceptual relationship graph built from room categories.

## 6.2 Fixed relation edges

The graph includes these type-to-type relations:

| Relation | Relation cost |
|---|---:|
| Kitchen ↔ Dining | 0.5 |
| Living ↔ Kitchen | 1.0 |
| Living ↔ Veranda | 0.5 |
| Living ↔ Bedroom | 2.0 |
| Bedroom ↔ Attached bathroom | 0.5 |
| Bathroom ↔ Living | 0.5 |

For ordinary relations, every instance of the first type connects to every instance of the second type.

If either room type is absent, that relation creates no graph edges and produces no direct penalty.

## 6.3 Attached-bathroom special handling

Attached bathrooms are not connected to every bedroom.

The code:

1. collects all bedrooms,
2. visits attached bathrooms,
3. connects each attached bathroom to the closest currently available bedroom,
4. removes that bedroom from availability,
5. continues until bathrooms or available bedrooms are exhausted.

### Apparent intent

Approximate one-to-one attachment by pairing each attached bathroom with a nearby bedroom.

### Important limitation

The pairing depends on attached-bathroom iteration order. It is a greedy nearest-available match, not a globally optimal assignment and not based on explicit room relationships.

## 6.4 Hallway edges

Every hallway connects to every point whose type is one of:

- living room,
- bathroom,
- dining room,
- kitchen,
- bedroom,
- hallway,
- garage.

Each hallway edge has relation cost `1.0`.

Hallways do not connect directly to verandas or attached bathrooms through this universal rule.

### Apparent intent

Treat hallways as general circulation connectors capable of providing indirect paths among most room categories.

## 6.5 Edge weight calculation

An edge's path weight is computed as:

```text
edge_weight = Euclidean distance × (1 + relation_cost)
```

Examples:

- relation cost `0.5` → distance multiplied by `1.5`,
- relation cost `1.0` → distance multiplied by `2.0`,
- relation cost `2.0` → distance multiplied by `3.0`.

The shortest path is selected using this weighted distance.

## 6.6 Important path queries

The evaluator defines eight room-type path queries:

### Public paths

- Veranda → Living room
- Living room → Kitchen
- Living room → Dining room
- Living room → Bathroom
- Kitchen → Dining room

### Private paths

- Living room → Bedroom
- Bedroom → Bathroom
- Bedroom → Attached bathroom

A query is active only when both endpoint room types are present in the candidate points.

If optional types are missing, the query is omitted and the available pathing score is redistributed across the remaining active queries.

## 6.7 Selecting an instance pair

For each active type query:

1. collect all start-room instances,
2. collect all end-room instances,
3. calculate a shortest graph path for every possible start/end instance pair,
4. ignore pairs with no graph path,
5. select the candidate path with the smallest weighted cost.

Only this best pair represents the entire room-type query.

### Apparent intent

When multiple rooms of the same type exist, reward the layout if at least one good functional connection exists between the queried categories.

### Important consequence

Other poorly connected instances of the same room type do not reduce that query's score.

## 6.8 Pathing score allocation

The pathing subsystem has a fixed maximum of `30` points.

If there are active queries:

```text
query_weight = 30 / active_query_count
```

If no path queries are active, the full `30` pathing points are awarded.

## 6.9 Maximum path-cost reference

The cost reference is:

```text
max_cost = max(1, floor_diagonal × 3)
```

where:

```text
floor_diagonal = sqrt(floor_width² + floor_height²)
```

For each active query:

```text
base_pair_score = query_weight × max(0, 1 - best_path_cost / max_cost)
```

Therefore:

- zero path cost would receive the full query weight,
- increasing cost reduces score linearly,
- cost equal to or greater than three floor diagonals receives zero.

## 6.10 Turn penalty

For a path containing at least three nodes, each internal junction is evaluated.

The code calculates the direction change between consecutive edges.

- turn angle up to `120°` → no penalty,
- turn angle above `120°` → proportional penalty,
- `180°` → full penalty for that junction.

Junction formula:

```text
junction_penalty = (turn_angle - 120) / 60
```

The final path turn penalty is the average across all internal junctions.

The query score becomes:

```text
pair_score = base_pair_score × (1 - average_turn_penalty)
```

### Apparent intent

Discourage indirect routes that reverse direction sharply, because they may represent awkward or unrealistic circulation.

### Geometric interpretation issue

A straight path through three collinear nodes moving in the same direction has a `0°` direction change and no penalty. A reversal toward the previous direction approaches `180°` and receives a high penalty. Therefore this is mainly a backtracking penalty, despite being described as a sharp-turn penalty.

## 6.11 No-path behaviour

If an active query has no routable graph path:

- it receives zero points,
- a critical log entry is emitted,
- a diagnostic path summary records `no_path`.

The query remains part of the active-query denominator.

## 6.12 Hallway crossing tracking

After selecting the best path for each query, every hallway node on that path records whether the query was public or private.

For each hallway:

```text
public crossing count
private crossing count
list of associated queries
```

Hallways never used by a selected path are also identified.

## 6.13 Hallway privacy score

The hallway privacy subsystem has a fixed maximum of `10` points.

If there are no hallways, or no hallway is crossed by any selected route, it awards the full `10` points.

Otherwise, each crossed hallway receives:

```text
1.0                         when total crossings == 1
abs(public - private) / total crossings   when total crossings > 1
```

The section averages these values across crossed hallways and multiplies by `10`.

Examples:

- one public crossing → `1.0`,
- one private crossing → `1.0`,
- two public and zero private → `1.0`,
- one public and one private → `0.0`,
- three public and one private → `0.5`.

### Apparent intent

Reward hallways that predominantly serve one circulation character—public or private—and penalize hallways that mix public and private traffic evenly.

## 6.14 Final relation score

```text
raw_relation_score = pathing_score + hallway_privacy_score
```

The raw score is clamped to the configured relation-section maximum.

Internally, pathing and privacy have fixed combined capacity:

```text
30 + 10 = 40
```

The configured relation maximum may or may not equal `40`.

## 6.15 Diagnostics produced

The evaluator returns:

- room-name to room-type mapping,
- graph node count,
- graph edge count,
- best-path summary for every active query,
- the actual NetworkX graph object,
- active-query count,
- hallway crossing information,
- hallway point objects that were not used by any selected path,
- warning when some predefined path queries were omitted.

## 6.16 Intended scoring behaviour

The intended concept appears to be:

> Reward candidate arrangements whose important room categories can be linked through short, functionally meaningful, low-backtracking routes, while encouraging separation between public and private hallway traffic.

This combines three separate concerns:

1. functional proximity,
2. conceptual circulation efficiency,
3. circulation privacy.

## 6.17 Review findings

### Valid ideas

- room relationships are one of the most important candidate-search signals,
- optional room types should change which checks are applicable,
- multi-instance room types require explicit instance-handling policy,
- route distance and route shape can both matter,
- public/private circulation mixing is a meaningful architectural concern,
- missing graph routes should be visible in diagnostics.

### Relation-cost ambiguity

The name `cost` suggests that a lower value represents a more desirable relation, but every edge weight is distance multiplied by `1 + cost`.

This means a relation with cost `2.0` is three times as expensive as its geometric distance, while a preferred relation with cost `0.5` is 1.5 times its distance.

Because the graph contains only selected relationship edges, these values appear to serve as traversal multipliers, but their architectural meaning is not documented clearly.

### Graph-model limitations

- edges are created from hard-coded room-type rules rather than the actual generation specification,
- the graph assumes conceptual traversability without doors or room boundaries,
- all hallways connect universally regardless of distance or obstruction,
- direct relations connect every instance pair and may create unrealistic shortcuts,
- veranda and attached bathroom connectivity is incomplete outside specific edges,
- garage is represented by a raw string in one location,
- a NetworkX object leaks into the public diagnostics.

### Multi-room limitations

- only the best instance pair is scored for each type-level query,
- one well-positioned bedroom can hide poor placement of all other bedrooms,
- bedroom-to-attached-bathroom pairing is greedy and order-dependent,
- relationship requirements supplied by the user are not used.

### Score-scaling risks

- internal maxima are fixed at 30 and 10,
- the final score is merely clamped to the configured maximum,
- if configured maximum is below 40, high results are truncated,
- if configured maximum is above 40, the evaluator can never reach it,
- no proportional normalization maps the internal 40-point scale to the configured maximum.

### Privacy-score concerns

- full privacy points are awarded when no hallways exist,
- full privacy points are awarded when hallways exist but no selected route uses them,
- unused hallways do not reduce the score,
- only best paths influence crossing counts,
- equal mixing is penalized most, but overall traffic volume has little effect,
- a hallway with one crossing receives a perfect score regardless of its role.

### Path-shape concerns

- the turn threshold is very tolerant,
- the metric mainly detects backtracking rather than ordinary awkward bends,
- direction changes are calculated from point centres rather than actual corridor geometry.

### Behaviour that should not be copied automatically

- hard-coded relation and path-query tables,
- awarding full pathing score when no queries are active,
- awarding full privacy score when no hallway evidence exists,
- using only the best instance pair by default,
- clamping a fixed 40-point internal scale against an unrelated configured maximum,
- interpreting the graph as real circulation.

---

# 7. Spatial-coverage scoring

## 7.1 Architectural quality being approximated

This evaluator tries to prevent candidate room points from:

- clustering heavily in one region,
- leaving large unrepresented areas of the floor,
- having highly irregular local spacing.

It combines two mathematical signals:

1. nearest-neighbour-distance uniformity,
2. grid-sampled coverage-gap size.

The evaluator scores all room points equally, regardless of room type or room size.

## 7.2 Nearest-neighbour uniformity sub-score

### Boundary anchors

The code creates twelve fixed boundary anchor points:

- four corners,
- four edge midpoints,
- quarter and three-quarter points on the top edge,
- quarter and three-quarter points on the bottom edge.

There are no quarter anchors on the left and right edges.

### Effective nearest-neighbour distance

For each room point:

1. find distance to the nearest other room point,
2. find distance to the nearest boundary anchor,
3. use the smaller of the two.

For a single room point, room-to-room distance is treated as infinity, so only its nearest boundary anchor determines the value.

### Uniformity calculation

From all effective nearest-neighbour distances:

```text
mean_nnd = mean(distances)
std_nnd = standard_deviation(distances)
CV = std_nnd / mean_nnd
```

The score is:

```text
nnd_score_100 = 100 × exp(-CV × 8)
```

The exponent is limited to no less than `-10`.

Consequences:

- identical effective distances → CV `0` → score `100`,
- modest variation causes a strong exponential score drop,
- the score evaluates uniformity, not whether the absolute spacing is good.

The code also calculates an ideal-distance reference:

```text
sqrt(floor_area / number_of_points)
```

but this value is diagnostic only and does not affect the nearest-neighbour score.

### Apparent intent

Encourage an even distribution of candidate points and reduce local clumping, while considering proximity to selected boundary locations so points do not all cluster centrally.

## 7.3 Grid-sampling coverage sub-score

The floor is sampled with a `20 × 20` grid, including boundary locations.

For every probe point, the evaluator calculates distance to the nearest room point.

It records:

- mean probe distance,
- 95th percentile probe distance, named `max_gap`.

The 95th percentile is used instead of the true maximum to reduce sensitivity to isolated edge probes.

### Theoretical reference

```text
ideal_distance = sqrt(floor_area / number_of_points)
theoretical_min_max_gap = ideal_distance / sqrt(2)
normalised_gap = percentile_95_gap / theoretical_min_max_gap
```

The score is:

```text
grid_score_100 = clamp(
    100 × (1 - (normalised_gap - 1) / 0.5),
    0,
    100
)
```

Therefore:

- gap ratio `1.0` or below → `100`,
- gap ratio `1.25` → `50`,
- gap ratio `1.5` or above → `0`.

### Apparent intent

Measure whether the room points collectively cover the whole floor without leaving large spatial voids.

## 7.4 Combined score

The two sub-scores are combined as:

```text
combined_100 = 0.40 × nnd_score_100 + 0.60 × grid_score_100
```

This combined percentage is scaled to the configured spatial-coverage maximum and clamped.

## 7.5 Missing-input behaviour

If no room points are provided, the section score is zero and a warning is emitted.

## 7.6 Warnings

The evaluator emits an irregular-clustering warning when:

```text
std_nnd > mean_nnd × 0.8
```

Equivalent to coefficient of variation above `0.8`.

It emits a coverage-void warning when:

```text
normalised_gap > 1.3
```

## 7.7 Diagnostics produced

The evaluator records:

- final and combined scores,
- both sub-scores,
- both weights,
- mean and standard deviation of nearest-neighbour distances,
- diagnostic ideal spacing,
- every effective nearest-neighbour distance,
- grid resolution,
- 95th-percentile and mean probe gaps,
- normalized gap ratio,
- ideal grid distance,
- the full 20 × 20 probe-distance matrix,
- room-point count,
- floor area.

## 7.8 Intended scoring behaviour

The intended concept appears to be:

> Reward candidate point sets that are distributed relatively evenly across the available floor and that do not leave large uncovered regions.

The sub-scores represent related but distinct concerns:

- nearest-neighbour variation detects inconsistent local spacing,
- probe-grid gaps detect large empty regions.

## 7.9 Review findings

### Valid ideas

- spatial distribution is useful before expensive solving,
- combining local-spacing and global-gap measures is stronger than either alone,
- scaling by floor area and point count is important,
- percentile-based gap measurement is more robust than a single worst probe,
- returning quantitative diagnostics supports tuning.

### Major conceptual limitation

Candidate room points represent rooms of different expected sizes. Uniformly distributing their centres across the entire floor is not necessarily architecturally correct.

A compact, adjacency-rich arrangement may be penalized even when it is desirable, while excessive spreading may score well despite creating long circulation paths.

### Nearest-neighbour limitations

- the score measures only variation, not absolute closeness,
- a uniformly clustered pattern can receive a high NND score if effective distances are similar,
- boundary anchors are asymmetric because extra anchors appear only on top and bottom,
- boundary anchors are discrete rather than measuring distance to the actual boundary,
- points near the centre may be penalized or rewarded indirectly in non-obvious ways,
- the diagnostic ideal distance is not used in scoring,
- duplicate points can create zero means and unstable interpretations, though numerical division is protected.

### Grid-score limitations

- the theoretical reference assumes ideal square-like point coverage,
- it ignores room dimensions and expected occupied area,
- a fixed 20 × 20 grid may behave differently across extreme aspect ratios,
- probes include the floor boundary even though room centres may not reasonably approach it,
- the score strongly reaches zero once the gap ratio reaches 1.5,
- convex or rectangular floor assumptions are embedded; irregular buildable polygons are not represented.

### Interaction risk

This evaluator may conflict with other goals:

- room-relations scoring tends to pull related rooms closer,
- spatial coverage tends to spread points apart,
- zone scoring restricts certain types to selected regions.

The legacy manager simply adds the section scores, without documenting how these competing forces should be balanced.

### Behaviour that should not be copied automatically

- treating every room point as equal spatial coverage mass,
- fixed mathematical constants without domain calibration,
- discrete boundary anchors as a proxy for floor-edge distribution,
- including large debug matrices in normal result data,
- assuming a rectangular floor based only on width and height.

---

# 8. Legacy score-manager behaviour

## 8.1 Execution order

The manager:

1. converts sampled values into room points,
2. evaluates floor-plan zones,
3. evaluates outer clearance,
4. evaluates room relations,
5. evaluates spatial coverage,
6. sums the four section scores,
7. compares the total to a configured gate threshold,
8. returns the total, gate decision, section results, room points, and diagnostics.

## 8.2 Total score

```text
total_score =
    zone_score
    + outer_clearance_score
    + room_relations_score
    + spatial_coverage_score
```

No normalization is performed at manager level.

The code prints a total out of `90.0`, but the actual possible total is determined by external configuration and the internal limitations of each evaluator.

## 8.3 Candidate gate

```text
usable_layout = total_score >= configured_gate_threshold
```

The name `usable_layout` overstates the evidence. The input is only a candidate point arrangement, not a validated layout.

The actual intended meaning appears to be:

> This candidate scored highly enough to continue to the next, more expensive generation stage.

## 8.4 Returned data

The result includes:

- total score,
- Boolean gate decision,
- section score map,
- complete section-result map,
- converted room points,
- combined diagnostics and warning groups.

## 8.5 Side effects

The manager and some evaluators print debug information during normal scoring.

The public `save_debug_plots` parameter is accepted but not used by the manager.

## 8.6 Intended manager behaviour

The intended concept appears to be:

> Act as a central orchestrator that evaluates one candidate through multiple independent quality dimensions, combines their contributions, and supplies both an Optuna-compatible scalar and diagnostic evidence.

## 8.7 Review findings

### Valid ideas

- one orchestration point is useful,
- Optuna needs a scalar objective value,
- retaining per-section results is valuable for analysis,
- a gate can prevent expensive downstream work on poor candidates.

### Structural and behavioural risks

- section registration is hard-coded,
- section names are duplicated as strings,
- section maxima are sourced inconsistently,
- total maximum is printed as a constant rather than calculated,
- no manager-level validation verifies score finiteness or evaluator bounds,
- no policy distinguishes failed, skipped, and not-applicable sections,
- one evaluator failure would interrupt the complete scoring call,
- debug printing is mixed into production behaviour,
- the gate uses an absolute total whose meaning changes whenever weights change,
- the result duplicates similar information across several dictionaries.

---

# 9. Combined scoring intent reconstructed from the package

Taken together, the legacy system appears to pursue this candidate-search objective:

> Find room-point arrangements that place important room categories in broadly suitable regions, preserve likely exterior-access corridors, keep functionally related rooms connected through short and reasonably direct conceptual routes, separate public and private circulation where possible, and distribute the full set of room points without severe clustering or large unused regions.

This can be broken into five architectural intentions:

## 9.1 Regional suitability

Selected rooms should occupy broad areas appropriate to their role.

Examples:

- veranda near the front,
- garage near a front corner,
- living room toward the front or middle,
- hallway away from the front,
- kitchen and bathroom away from the exact centre.

## 9.2 Exterior accessibility

Selected rooms should have open directional space for likely external access.

Examples:

- veranda frontage,
- garage approach,
- kitchen or hallway rear exit.

## 9.3 Functional proximity

Frequently related room categories should be reasonably close.

Examples:

- kitchen and dining,
- living and veranda,
- bedroom and attached bathroom.

## 9.4 Circulation quality and privacy

Important public and private destinations should have short conceptual paths, avoid backtracking, and preferably use circulation routes that do not mix public and private traffic evenly.

## 9.5 Spatial distribution

The entire candidate set should avoid strong clumping and very large uncovered floor regions.

---

# 10. Important contradictions and overlapping signals

The four evaluators are not independent. Several rules push candidate points in opposing directions.

## 10.1 Compact relations versus spatial spread

Room-relations scoring rewards proximity and shorter paths.

Spatial-coverage scoring rewards distributed points and smaller global voids.

Without careful balancing, one evaluator may reward exactly what another penalizes.

## 10.2 Zone preference versus clearance

Zone scoring can place veranda and garage anywhere across the front row or front corners, but clearance scoring does not verify whether the room point is sufficiently near the actual exterior boundary.

A point may satisfy its zone yet have a “front clearance” rectangle largely inside the floor.

## 10.3 Hallway placement versus hallway use

Zone scoring discourages hallways from the front row.

Room-relations scoring connects hallways universally and may use them as shortcuts regardless of realistic geometry.

Hallway privacy can then award full points when hallways are unused.

## 10.4 Room centres versus room sizes

All evaluators treat rooms as points.

Large and small rooms have equal representation, so:

- clearance blockers ignore room extents,
- coverage ignores room area,
- path distance ignores likely doorway locations,
- zone rules evaluate only a centre point.

This is acceptable only as a coarse candidate-search approximation and should be documented explicitly in the future design.

---

# 11. Behaviour classification for the redesign review

The following table classifies the recovered concepts. It does not make the final keep/remove decision; it identifies what deserves preservation or reconsideration.

| Legacy concept | Underlying intent | Initial classification |
|---|---|---|
| Soft preferred regions | Guide important rooms toward broadly appropriate locations | Preserve concept; redesign rules/configuration |
| Continuous distance falloff | Avoid abrupt score discontinuities at zone boundaries | Preserve |
| Veranda front openness | Maintain usable frontage | Preserve concept; replace point-box approximation |
| Garage approach openness | Maintain vehicle access | Preserve concept; make dimensions/config explicit |
| Rear-opening option | Encourage at least one rear access opportunity | Preserve concept; review source-room rules |
| Functional room relations | Keep related rooms near each other | Preserve; derive from explicit relation data |
| Conceptual graph paths | Estimate indirect connectivity | Review deeply; current graph is not real circulation |
| Public/private path classes | Represent circulation privacy | Preserve concept |
| Backtracking penalty | Discourage awkward indirect routes | Review metric and terminology |
| Hallway specialization | Reduce public/private traffic mixing | Preserve concept; redesign evidence and applicability |
| NND uniformity | Detect irregular point clustering | Review; may be too abstract for room centres |
| Global gap detection | Detect large uncovered regions | Preserve concept cautiously; account for room sizes and usable boundary |
| Weighted section total | Combine several quality dimensions | Preserve; redesign normalization and configuration |
| Absolute gate threshold | Filter poor candidates before expensive solving | Preserve gate concept; prefer stable normalized meaning |
| Full score for not-applicable checks | Avoid penalizing absent optional features | Replace with explicit applicability policy |
| Silent omission of missing points | Keep scorer running on incomplete data | Reject for new design |
| Hard-coded room-type strings and names | Simplify legacy integration | Remove |
| Arbitrary diagnostic dictionaries | Support debugging quickly | Replace with standardized results/findings |

---

# 12. Questions that must be resolved before designing the replacement

## 12.1 Candidate semantics

- Does each point represent a room centre, a preferred seed location, or only a solver hint?
- Are generated hallway points equivalent to requested room points?
- Should every required room always have exactly one candidate point?

## 12.2 Orientation and boundary

- How is front, back, left, and right defined for every floor?
- Will scoring use only rectangular floor dimensions or the actual buildable polygon?
- Should directional rules be relative to road access or user-selected facade orientation?

## 12.3 Zone rules

- Which room types truly need regional preferences?
- Should rules come from room type, project configuration, or room-specific constraints?
- Should preferred regions be rectangles, bands, distance fields, or semantic zones?

## 12.4 Exterior access

- Which rooms require exterior access?
- Is one rear exit sufficient, or can requirements specify multiple exits?
- Should garage clearance use vehicle dimensions and driveway direction?
- Can exterior access be estimated meaningfully before room geometry exists?

## 12.5 Relations and circulation

- Should relation scoring use the planned `RoomRelationSpec` rather than fixed type tables?
- How should AND/OR relation policies affect scoring?
- Should all instances be evaluated, the best instance, the worst instance, or explicit room-ID pairs?
- Can hallway points form a meaningful circulation graph before geometry exists?
- What exactly distinguishes public and private routes?

## 12.6 Spatial distribution

- Is uniform spread genuinely desirable, or is compactness more important?
- Should room size affect expected spacing?
- Should coverage be measured against the actual usable floor polygon?
- Should coverage reward occupied-area potential rather than point distribution?

## 12.7 Score meaning

- Should every evaluator return a normalized `0..1` quality value?
- How should not-applicable evaluators affect the denominator?
- Are some findings severe enough to act as gates rather than weighted preferences?
- Should the Candidate Search objective maximize total quality, minimize penalty, or use multiple objectives?

---

# 13. Final recovered specification

The legacy package is best understood as a **candidate hint quality evaluator**, not a floor-plan validator.

Its intended functional contract can be summarized as:

```text
Input
    Floor dimensions and room requirements
    One proposed point for each candidate room/node
    Scoring weights and a continuation threshold

Evaluation
    Regional suitability
    Directional exterior-access opportunity
    Functional relationship and conceptual route quality
    Public/private hallway-use separation
    Global point distribution

Output
    Bounded score for each quality dimension
    Combined candidate score
    Decision whether the candidate should proceed
    Explanatory diagnostics
```

The architectural ideas are useful, but the implementation mixes intentional heuristics with accidental assumptions. The new scorer should preserve only the reviewed domain goals, not the legacy formulas or code organization by default.

The next design stage should use this document as the behavioural source and make an explicit decision for every evaluator:

```text
Preserve as-is
Preserve concept but redesign formula
Merge with another evaluator
Replace with a different signal
Remove
```

Only after those decisions are documented should the replacement scoring architecture and evaluator contracts be finalized.
