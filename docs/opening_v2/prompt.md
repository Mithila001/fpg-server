Our Gola is to implement a Bran New FPG Opening feature for my project. If you look at the project you can see i already have a Opening setup implemented at `app\algorithms\fpg_opening` the problem here is that it use older floor plan structure for their logic. But now i got a new floor plan data structure in ProcessedRoomData dataclass and this new ProcessedRoomData cannot work with existing opening generator.
So I plan to create new opening generator at app\algorithms\fpg_opening_v2 with is identical of what app\algorithms\fpg_opening do for the floor plan, But this fpg_opening_v2 is entirely made for work with a floor plan type list[ProcessedRoomData]

When come to "What Should Achieve" it fairly identical to what Achieve at `app\algorithms\fpg_opening`. But the new part her is "How to Achieve" since now we have to work with a new data type list[ProcessedRoomData]

You can look at `app\algorithms\fpg_opening` to get and idea about what we doing here and find some answers if you have some problems, But do not give too forcus on it, This `app\algorithms\fpg_opening_v2` should not connect with `app\algorithms\fpg_opening` files
Cause I will remove `app\algorithms\fpg_opening` from the project once fpg_opening_v2 becomes usable.

I also created new files and folder withing app\algorithms\fpg_opening_v2 in advance.

Also we have good opportunity to avoid `app\algorithms\fpg_opening` implemented mistakes (if any exist only) and implement better \fpg_opening_v2

Implement a matplotlib (No UI display) fpg_opening_results_plotter() function code and save the image (with time stamp) at `test\outputs\openings`
After a successfully Opening Generation, call fpg_opening_results_plotter() withing generate_fpg_openings() function and plot the results so i can see if its actually working as expected.

Return the floor plan type FloorPlanWithOpenings from generate_fpg_openings()

I have created new Data type for Return data type (modify if you want)

app\algorithms\types\openings.py

@dataclass
class FloorPlanWithOpenings:
floor_plan: list[ProcessedRoomData]
openings: list[OpeningData]

@dataclass
class OpeningData:
room_name: str
room_type: str
opening_type: str
side: str
x1: float
y1: float
x2: float
y2: float
connected_room_name: str
connected_room_type: str
