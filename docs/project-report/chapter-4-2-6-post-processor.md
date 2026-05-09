### Chapter 4.2.6 Post Processor

This Section focus on post processing the CP-SAT solver generated Floor plan
Initially the post process implementation was a simple process that primary focus on processing the floor plan in order to send for the client in more clear and consist manner.
But Due to Solver + refiner provided floor plan not passing the minimum requirement to be the floor plan due to small mistakes frequency becomes higher, A solution required adjust those small mistake with pre define rules instead of complicating and hardening the CP-SAT solver constrains, witch caused higher infeasibility and lower quality floor plan due to constraint conflicts in initial testing.
So more advance post processing system was implemented and place between Floor Plan Generator and Floor Plan scoring System.
The implementation of post processing system is the most influential system that increase the usable floor plan generation system.

Some could argue this would damage the goal of heavy constrain based generated floor planes, But after testing the results, The Const bensitifits gap is significant and the floor plan scoring system filtering `bad` plan out of post process plan make this post process implementation a solid choice.

Also the post process feature enable to generate non convex room shapes compare to previous rectangle only room shapes

Below are the Post Processing Concepts that implementing the floor plans.

#### Extended wall post process

This is one of the most advance post processing feature this system have. <`Explain the Concept and uncased in depth`>
<`Talk about this Extended wall post process room extending configuration worked`>
<`Ignore Dev Related Plotting`>

#### Hallway Union

<`Explain how this work and how it benefits`>

#### Snap Floor Plan to Grid

<`Explain how this work and how it benefits`> <`Explain this avoid very long decimal numbers and will not change the floor plan room dimentions noticeable level `>

#### Explain Veranda Post Process

<`Explain how this work and how it benefits`>

#### Wall Union

<`Explain how this work and how it benefits`>

#### Chapter Ending

<`Ignore app\algorithms\fpg_post_processor\post_processor_main.py since it not mainly part of this`>
