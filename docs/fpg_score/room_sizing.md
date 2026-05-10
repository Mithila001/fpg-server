We going to implement basic scoring feature at `app\algorithms\fgp_score\score_functional\basic`

These are the sub scoring logics. Each logic required dedicated python file at `app\algorithms\fgp_score\score_functional\basic\util` should call and use in the `app\algorithms\fgp_score\score_functional\basic\basics.py`
Each sub scoring logic should return the score out of 100.

1. Check if the livingRoom area is >= rest of the room are combined. If false, return 100, else, based on how larger the living room is, lower the score
2. Check if the Bedrooms are lower that 900 units. If do, give heavy penalty. Additionally check, how the area difference between all room type bedrooms. (should be able to take account more that 2 bedroom here) and if the area differ is higher, give lower score. Total score is out of 100
3. Check if the kitchen and dining room have shared wall, if do, give 100, else calculated the distance between two room center points, lower the score if the distance is higher.

Now at `app\algorithms\fgp_score\score_functional\basic\basics.py` call each one and provide the data for those function and get the results, Now this main function should gather all marks, and normalize it be score out of `score_margin: float` and return the score.
