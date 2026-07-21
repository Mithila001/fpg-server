# Hallway Geometry Constraint Update

## Objective

Update the solver so that hallway geometry is controlled by a dedicated hallway constraint rather than the generic room aspect ratio constraint.

---

## 1. Exclude Hallways from the Aspect Ratio Constraint

The existing aspect ratio constraint should no longer apply to hallway rooms.

Only non-hallway room types should be evaluated by the aspect ratio constraint. Hallways should be completely ignored by this constraint so they are free to become long corridors without violating the room aspect ratio rules.

---

## 2. Introduce a Dedicated Hallway Dimensions Constraint

Create a new hard constraint responsible only for hallway dimensions.

This constraint should apply exclusively to hallway rooms.

If a hallway exists in the generated layout, it must satisfy the following rule:

* One dimension (either width or height) must be between **8 and 10 project units**, inclusive.
* The other dimension is allowed to extend as necessary to form the corridor.

This allows hallways to become long horizontal or vertical corridors while maintaining a realistic corridor width.

Examples:

* Horizontal hallway

  * Height: 8–10 units
  * Width: unrestricted

* Vertical hallway

  * Width: 8–10 units
  * Height: unrestricted

The constraint should not require a specific orientation. Either horizontal or vertical hallways are acceptable as long as one side remains within the allowed corridor width.

---

## Expected Behavior

After this change:

* Regular rooms continue to obey the existing aspect ratio constraint.
* Hallway rooms no longer use the aspect ratio constraint.
* Hallway rooms instead use the dedicated hallway dimensions constraint.
* Hallways are therefore allowed to become long corridor-shaped spaces while still maintaining a realistic corridor width.
