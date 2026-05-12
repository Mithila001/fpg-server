### Chapter 4.2.4 Optuna Scoring System

This is the Scoring System for the Optuna Sampling System
The Main Goal here is to Direct Optuna to Sample Valid Floor plan generation Point hints for the CP-SAT solver in a way that provide Hight probability for Solver to use those hints to generate a Floor plan without getting infeasible results. To Achieve this, the system implement a advance scoring system that specifically focus on optuna sampling

The primary goal of the scoring system is to guide Optuna toward sampling 'Hint Points' that maximize the solver's success rate. By assigning higher scores to samples that lead to feasible, high-quality layouts and penalizing those that result in infeasible states, the system creates a gradient for Optuna to follow. This advanced scoring mechanism ensures that the CP-SAT solver receives high-probability starting points, significantly reducing the computational time spent on infeasible search branches.

To facilitate efficient learning, the scoring system avoids binary 'success/fail' flags in favor of a continuous scoring range (ex: 0–100). This approach provides Optuna with a dense reward signal, allowing the TPE sampler to distinguish between 'nearly valid' and 'completely invalid' hint points, effectively smoothing the search landscape.

The scoring logic follows a tiered threshold strategy:

- Feasibility Phase (0–90 points): The first 90 points are allocated based on the Optuna sample Results. The other 10 is from CP-SAT solver generate floor plan scoring <`Explain this part more clearly. About how the scoring is divided and the sub looping strategy`>
- <`Briefly Explain this Setup Enable for fast First Phase Scoring +Trial process and only Run heavy CP-Sat solver for highers scored point hint layouts`>

Now talk about what getting score.
<`Briefly Explain about the score manager who manage scoring logic. explain the scoring logic capability to scale with new scoring concepts.`>

Below will explain the each scoring Concept that used.

#### Zoning Score

Main Goal here is to guiding optuna to plane specific rooms on specific zone that beneficial for CP-SAt Solver constrains.
<`Explain The Concept more in-depth`>
<`Explain what are Current Implemented Zoning Rules`>
<`Here I do not think there are formulas to be added here`>
<`Avoid talking about scoring logic in depth`>
<`Avoid talking about dev plotting or prints if exist`>

#### Outer Clearance Score

Reason is to Place some Room points that have outer clear on specific side
<`Explain the concept more in-depth`>
<`Explain what are the current implemented outer clearance Rules`>
<`Avoid talking about scoring logic in depth`>
<`Avoid talking about dev plotting or prints if exist`>

#### Room Relation Score

This guide Optuna to Place specific rooms closer to each other
<`Explain the concept more in-depth (including patting construction and simulation)`>
<`Explain what are the current implemented relation Rules`>
<`This scoring setup will have bit more that rest of the soarings to explain`>
<`Avoid talking about dev plotting or prints if exist`>

#### Spacial Coverage Score

To avoid placing Point too closer/clustered to each other and also avoid void space in the search space. guiding points to roughly evenly spread across the floor plan space.
<`Explain the concept more in-depth`>
<`Avoid talking about scoring logic in depth`>
<`Avoid talking about dev plotting or prints if exist`>
