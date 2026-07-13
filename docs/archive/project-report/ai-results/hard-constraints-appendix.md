# Appendix: Hard Constraints in the Spatial Synthesis Model

This appendix summarizes the hard constraint layer that governs admissible layouts. The thesis already covers the broader generation strategy, so the emphasis here is on the role of each constraint family, the configuration it accepts, and the practical effect it has on the plan.

| Constraint family             | Main purpose                                                | Adjustable parameters                                                        |
| ----------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| General geometry              | Prevent overlap and unrealistic proportions                 | Aspect bounds by room type                                                   |
| Hallway behavior              | Preserve corridor-like form and contact                     | Narrow-side range, long-side minimum, shared-wall requirement                |
| Frontage and exterior reserve | Fix street-facing placement and reserve outdoor space       | Front boundary alignment, exterior reserve dimensions                        |
| Vehicular annex placement     | Keep the garage near a side boundary with access logic      | Side-anchor threshold                                                        |
| Spatial hierarchy             | Organize rooms by depth and relative importance             | Relative area bands, frontage anchor rule                                    |
| Adjacency and shared walls    | Enforce functional connectivity and sufficient wall contact | Minimum overlap, required partner types, wall-count limits, tolerance margin |
| Back-wall setback             | Preserve clear space behind selected service rooms          | Minimum and maximum clear depth                                              |
| Coverage                      | Ensure the floor is sufficiently used                       | Minimum coverage ratio                                                       |

## 1. General geometric admissibility

The foundation of the hard layer is a geometric validity rule. Every room must remain non-overlapping, and its start and end coordinates must remain consistent with its width and height. In addition, most room types are restricted by aspect ratio so that the solver does not produce unrealistically thin or flattened shapes.

The hallway category is treated differently because corridors are intentionally elongated. Other rooms use a default proportional range, while certain special rooms such as garages and verandas may use tighter or more permissive proportions to reflect their functional character.

## 2. Hallway behavior

Hallways are not merely ordinary rooms with a different label. They are constrained to behave like circulation spines. The solver encourages a narrow cross-section but requires a meaningful longitudinal extension, which prevents hall-like spaces from becoming square blocks or decorative gaps.

The hallway logic also checks contact with other spaces. A valid hallway must connect to the living area and, depending on the project configuration, additional rooms may be required to touch it as well. This keeps circulation useful rather than isolated.

## 3. Frontage and exterior reserve

The frontage layer anchors the veranda at the front edge of the plan and reserves an adjacent outdoor zone. That reserve is treated as a structural buffer rather than free residual space, so it cannot be invaded by other rooms.

Only one lateral side of the veranda may attach to this reserve, which produces a controlled stepping of the outer outline. This rule helps the frontage read as a deliberate architectural threshold between street and interior.

## 4. Vehicular annex placement

The garage is constrained to sit near exactly one vertical side of the plan. This avoids central placement and gives the vehicle space a clear boundary identity. A second rule governs access: the garage must either open directly to the front edge or align with a frontage reserve so that access remains plausible.

This combination handles common edge cases such as ambiguous central garages or garages that are side-anchored but disconnected from the arrival zone.

## 5. Spatial hierarchy

The hierarchy rules organize the plan by depth and relative program weight. The frontage anchor, usually the veranda when present, is kept nearer to the front than the remaining rooms. In layouts without that element, the living area assumes the anchoring role.

A separate proportional rule ensures that selected room types remain within an acceptable area band relative to the living space. This prevents secondary rooms from becoming unrealistically dominant or excessively undersized.

## 6. Adjacency and shared walls

Adjacency constraints express mandatory functional relationships. Some rooms must touch a specific counterpart directly, while others may satisfy the requirement through an intermediate circulation space. The contact is not counted as valid unless a minimum overlap exists, which avoids accidental corner contact being treated as a true connection.

Shared-wall rules complement adjacency by controlling how many room sides may be meaningfully shared and how complete that sharing should be. A small tolerance margin is allowed in some cases, which improves robustness without weakening the architectural intent.

## 7. Back-wall setback and coverage

Selected service rooms require a clear strip behind their back wall. The purpose is to preserve practical clearance for movement, door placement, or maintenance. The rule is flexible enough to accept a range of usable depths, but it rejects layouts where another room intrudes into that reserved zone.

Finally, the coverage rule ensures that the assembled rooms occupy a sufficient portion of the floor plate. This guards against sparse or underdeveloped solutions that technically satisfy local rules but fail as complete layouts.

## Reviewer Notes

- Specific implementation identifiers were intentionally omitted and replaced with conceptual descriptions.
- Only constraint families with distinctive architectural behavior were expanded; routine geometric bookkeeping was summarized briefly.
- The description follows the project’s actual hard-constraint behavior while avoiding unnecessary mathematical detail.
