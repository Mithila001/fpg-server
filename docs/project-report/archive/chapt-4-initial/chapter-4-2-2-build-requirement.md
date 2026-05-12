### Chapter 4.2.2 Build Requirement

This is the Section that Process the user provided Floor Plan Requirements into a payload that suitable for the Floor Plan Generation Pipeline. The Core Task of this section would be

- Validate the user provided floor plan requirements
- Get required database data
- Mutate the requirements to compatible with Floor plan generation flow

Below will explain the work flow of how the process happen withing the build requirement section

#### Validation

Validate Data that if the room template contain the mandatory room that required for the generation.
<`provide small example of what kind of room type that needed. and briefly explain those rooms are mandatory due to CP-SAT generation strictly required it for the generations`>

#### Dimension Calculation and Aspect Ratio

This section reduce the floor plan space based on room required to avoid giving too large search space for the Floor Plan Generator. <`Explain the calculation part. Provide Formulas`>
The user can provide aspect ratio for the floor plan. In this section those values are taken and do feasibility check on to check if these aspect fit with buildable space and if not, adjust the aspect ratio accordingly.
<`explain how the aspect ratio adjustment logic work`>
<`provide the main formulas use for this process if only exist`>

#### Load Server Constrains

Retrieve room size constrains data and Room Relationship data that required for for the floor plan generation. Room size constrain contain data about each room min max w,h bases on size category <`Provide a small example`> and Room Relation constraint contains the relationship data between two types of room. <`Provide an example room relation data`> Here this <`Explain each object keys like constraint_level, related_room, .. usage briefly`>.This relationship data is to as constraint in CP-SAT solver.

#### Majority size selection

Inspect the template to pick a dominant room-size label (e.g., "regular") by counting size occurrences and convert all room to the majority room size category. This is mainly a safety mechanic do to project limitation on expecting with relativity conceit sized of the room sized.

#### Prune Relations

This section modify the room relations constraints data to compatible with given floor plan requirements. <`Explain an example where a room does not exist in the room template but exist in the relation constrain could cause issues`>

#### Assemble Final Package

After every process, this section crete a single object with all the requirement data that required for the rest flow. This object will be use by almost everywhere in the rest of the project

### Overall Assessment

Overall this this the pre process and pre validation area of the system before the actual floor plan generation process. <`Talk about bit of how the overall build requirement section look like and behave and contribution the system`>
