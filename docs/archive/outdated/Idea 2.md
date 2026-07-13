Ok, I need you to read this #file:Post-Process-Solver-Idea.md  first, and listen to what im saying.

I was thinking about this lot, And other that implementing this accurately, Other one of major issues im facing is this new FPGF implementation is breaking the FPGR rules during the process. I can say in FPGF to copy all the important constraints from FPGR, but that not sound good on paper. So i thought about this and only solution i can come up was this.

Instead of creating a new setup `app/algorithms/fpg_finalize` We can make `app/algorithms/fpg_rooms` dual state setup. 

From my understanding, One of main 2 cause that CP-SAT solver take so many time to get a feasible results is: 1. Larger Search Space to look at  2. Lot of Constraints.

The second run (Formally FPGF) also required to follow FPGR constraints. I will explain this in a example.
Ok so Assume our current FPGR have A,B,C,D constraints. And current our issues is we have E,F,G new constraint we need to add, But the problem is A,B,C,D + E,F,G total constraint is too heavy. And E,F,G required A,B,C,D constrain in order to give a useful results, so we cannot just run E,F,G in another setup with results from A,B,C,D as well.

My proposal is to add A,B,C,D,E,F,G at FPGR, BUT instead of everything running in `app/algorithms/fpg_rooms/generator.py` we replace those with new two generator python files, `fpgr_generator_1.py` and `fpgr_generator_2.py`

`fpgr_generator_1.py` will do current existing generation and `fpgr_generator_2.py` will do new generation

And both files can share constraints if they wanted. Only difference is generator 1 create new floor plan and generator 2 use existing floor plan 

Actually, we can do better, we can create a parent abstract class that have comment implemented logic and inherit them to generator 1 and 2. This way these generator 1 and 2 will have clearer simpler code. 

Keep in mind if we go with this new concept i just mention here, some of the concept i mentioned at #file:Post-Process-Solver-Idea.md is not going to be use here

