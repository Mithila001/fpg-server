### Post-Processing Refinement Stage

The post-processing stage sits between generation and scoring. Its purpose is to repair layouts that are feasible in principle but still contain local geometric defects such as fragmented circulation, void spaces, misaligned boundaries, decimal drift, or weak frontage alignment. Rather than forcing the generator to resolve every detail upfront, the refinement layer applies limited corrections that preserve the plan’s spatial logic while improving usability and evaluation stability. It is best understood as conservative geometric repair rather than redesign.

#### Extended Wall Refinement

Extended wall refinement allows selected room boundaries to grow when a small extrusion improves continuity or adjacency. The operation is bounded by room-type priority and configuration limits, so only a limited number of rooms, wall candidates, and extrusion distances are considered. This makes the process selective: it can enrich a room outline, but it cannot distort the whole plan.

#### Hallway Union

Hallway union addresses fragmented circulation. When adjacent hallway segments share sufficient overlap in their boundaries, they are merged into a single circulation component. The result is clearer, more faithful to architectural convention, and less likely to be penalized by later scoring.

#### Snap Floor Plan to Grid

Grid snapping regularizes coordinates by projecting them onto a fixed lattice. If $g$ is the grid spacing, then \mathbit{x}^\prime=\mathbit{g}\cdot\mathrm{round}\left(\mathbit{x}/\mathbit{g}\right) and \mathbit{y}^\prime=\mathbit{g}\cdot\mathrm{round}\left(\mathbit{y}/\mathbit{g}\right) . This removes floating-point noise introduced by geometric operations and improves numerical stability without changing the plan in any meaningful architectural sense.

#### Veranda Adjustment and Wall Union

Veranda adjustment checks whether the veranda and its outdoor transition space are actually adjacent before any correction is applied. When alignment exists, the veranda frontage can be shifted to match the width of the adjoining outdoor region, improving continuity and reducing awkward projections. If the relationship is absent, the system leaves the geometry unchanged.
Wall union then consolidates overlapping or duplicate boundary traces into one structural network. This prevents double-counting, yields a clearer wall representation, and provides a stable base for opening placement and boundary validation.
