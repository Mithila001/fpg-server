### Chapter 4.2.5 Floor Plan Generator

This is the Core system of the Project. Responsible of generating actual floor plans. Taking Most computational power and time between all other components.

For the Floor plan generation, the system use Google OR-Tool CP-SAT solver. Due to floor plan generation requiring to follow strict rules while keeping acceptable level of diversity of floor plan generation.

The Profile system, control panel and Configuration is allowed to system to configure and experiment with various constrains patters

For this Chapter, Ignore
`app\algorithms\fpg_rooms\generator.py`
`app\algorithms\fpg_rooms\fpgr_p_refine_extender.py`
`app\algorithms\fpg_rooms\fpg_score`
`app\algorithms\fpg_rooms\fpg_post_process`
`app\algorithms\fpg_rooms\fpg_optuna`
`app\algorithms\fpg_rooms\fpg_graph`

#### Floor Plan Generation Core (Engine)

This is the main core of the Floor plan generator. (`app\algorithms\fpg_rooms\fpgr_core.py`)
<`Explain How this Section work as the core process`>
<`Explain how it initialized data, how variables are created for Solver, How i use Constrain Control panel `>
<`Tell about important unique Solver configuration that project set up that worth mentioning `>

#### Floor plan Generation Initialization profile

This is the Floor plan Generation Initialization profile. `app\algorithms\fpg_rooms\fpgr_p_generate.py`
<`Explain the Process In Depth, Explain the seeding, Explain that this is a profile. Explain This setup mainly focus on enforcing hard constrains for the generation`>

#### Floor Plan Generation Refinement Profile.

This is the Refinement Profile focus on refining the already generated plan with small step modifications.
<`Explain the concept in depth`>
<`Explain The How it worked with both Hard and Additionally adding soft constrains, Explain Limited step count to avoid major modification by the refiner. Explain How this refiner profile is can be and currently being called multiple times to get controller multi step refinement for the floor plan `>

#### Floor Plan Generation Constraints.

The are the main contributors of providing a final usable floor plan by solver. The constrain are separated in to 2 Section, Hard contains and Soft Constrains
<`Here ignore about app\algorithms\fpg_rooms\constraints\extenders due to it not being actively use by the current project`>
<`Give a small overview of how the constraints contributing to the Floor plan generation`>

<`Now you need to Explain Each Hard constrains in moderate details, Explain Each Hard Constrains one by one and Soft constrains one by one using ##### type headers per each constrains Some constraint might required small explanation while other will required more detailed explanations`>

#### End of this Chapter.

<`Give a small end info about this chapter`>

<`Ignore Dev Related Plotting`>
