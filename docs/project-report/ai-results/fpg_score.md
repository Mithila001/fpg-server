# Appendix: Floor Plan Scoring Logic

The scoring stage is the final evaluation layer applied after geometric post-processing. Its purpose is to determine whether a generated plan is sufficiently coherent to be accepted and, if so, to assign a final quality measure that combines structural validity with a smaller functional appraisal. The evaluation is intentionally hierarchical: geometric soundness is assessed first, and only fully valid plans are allowed to receive the supplementary functional contribution.
Before scoring begins, the system works with the post-processed room geometry and removes elements that are not relevant to the scoring envelope or that are too small to support reliable polygonal evaluation. This preliminary normalization ensures that the assessment is performed on a consistent spatial representation. If the resulting geometry is not rectilinear enough for reliable verification, the process ends immediately with no positive score.

## Critical geometric evaluation

The critical section consists of three checks, each worth one third of a 25-point geometric budget. If $p$ checks are passed out of $n$ executed checks, the critical score is calculated as

$$
S_{critical} = 25 \cdot \frac{p}{n}.
$$

This formulation gives the geometric stage a transparent and evenly distributed weighting scheme. Each check contributes equally, and the final value is bounded to the interval $[0, 25]$.

### 1. Adjacency validation

The first check examines whether required spatial relationships between room categories are satisfied. The evaluation is rule-based: some relations demand that one room category touches another specific category, while others allow contact with any room from a defined set. Contact is not treated as a simple point intersection; instead, the shared boundary must exceed a minimum overlap threshold to count as meaningful adjacency. This prevents incidental corner contact from being mistaken for a valid architectural relationship.

### 2. Empty-space validation

The second check identifies enclosed voids inside the assembled floor plate. The room polygons are combined into a single occupied region, and the system compares that region with the enclosing boundary derived from the union geometry. Any interior gap larger than the permitted tolerance is treated as a defect. This check protects against plans that appear complete in outline but still contain unused internal cavities that would weaken usability and structural clarity.

### 3. Inward-pocket validation

The third check measures the depth of recesses along the outer form of the layout. The occupied union is compared with its convex hull, and the difference reveals inward pockets in the envelope. The algorithm then inspects the relevant pocket segments and evaluates their inward extent against a maximum allowable length. If a recess exceeds that limit, the plan is considered to have an excessive indentation. This preserves a compact building silhouette and discourages overly irregular outlines.

## Functional supplement

Only when all three critical checks succeed does the system apply the functional supplement. This additional score occupies the remaining 75 points and is intended to distinguish stronger residential arrangements without compromising geometric validity. The functional measure is composed of three equally weighted sub-scores:

- balance of the living area,
- consistency of bedroom sizing,
- kitchen–dining relationship.

Each sub-score is first expressed on a $0$ to $100$ scale. Their arithmetic mean is then converted to the 75-point functional budget:

$$
S_{functional} = 75 \cdot \frac{r}{100},
$$

where $r$ is the average of the three functional sub-scores. The final score is therefore the sum of the 25-point geometric component and the functional supplement, but only in the fully valid case. If the critical section is not perfect, the functional stage is skipped entirely and the plan retains only its geometric result.

## Interpretation of the scoring model

This design reflects a clear architectural priority. Structural validity is treated as a prerequisite, not merely one preference among many. Once the plan satisfies the essential geometric conditions, functional quality can contribute additional merit. The result is a balanced evaluation framework in which compactness, adjacency, and envelope integrity form the foundation, while interior usability refines the final outcome.

## Reviewer Notes

- Path-simulation scoring was intentionally excluded because it is not part of the active scoring path.
- Implementation identifiers were replaced with conceptual descriptions to match thesis style.
- The appendix reflects the scoring logic actually used: rectilinear verification, three critical geometric checks, and the conditional 75-point functional supplement.
