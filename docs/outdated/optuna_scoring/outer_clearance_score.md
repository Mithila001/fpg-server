I want to compley change #file:outer_clearance.py file with this log. Do not keep any code that outdate. No backward compatibility.
Current #file:outer_clearance.py is messy and bloated. So this is my brand new implementation

score_outer_clearance() Gives you requirements: FpgRequirements, room_points: list[OptunaScorePoint]

Create function like this:
\_evaluate_veranda()
\_evaluate_garage()
\_evaluate_back_opening()

Each function will take data that need to evaluation

withing each function, the function will evaluate the clearance and return the marks out of 100

In most cased, this is a like a either 0 or full score will come from those evaluation functions.

But there are some cased like \_evaluate_back_opening() where the evaluation is bit more complex. Here the evaluation with those logic will calculate and return the score.

Within these each evaluation function there will be safety gate, where it check if the room exist in room_points before

So overall each evaluation function core body structure is like this

function(data):
<safety gate>
<customer rules if needed>
<evaluation logic>
return score, isEvaluvated

Here we return isEvaluvated = false in case where <safety gate> decide the room is not there for evaluate.

now withing score_outer_clearance(), it will first run all the \_evaluate functions And get the results. Now it got

- How many evaluation function actually scored (evaluvated_count)
- recived_score from all evaluations
  IMPORTENT: Here we should first ignore isEvaluated = False evaluation results, those will be not part of scoring processes

Now using evaluvated_count, we can score received out of full score. Example: if evaluvated_count = 2, and total recived_score = 150, the final_score is 150 out of 2\*100

Now we got final_score, and we can get max score that project gives us to work with by OPTUNA_SCORING_VALUES {take OPTUNA_SCORING_VALUES (OPTUNA_SCORING_VALUES: dict[str, float]) , witch have a data like this "optuna_score_clearance": 20,
}

get that and normalize the final_score out of that value and return to parent.

If we provide room_points as param for each evaluate function, then function it self can decide how many room in same type should get score. Example like in evaluate_back_opening(), we only need either kitchen (prirarty) or hallway for evaluation.

I believe this will simplify the code significantly, In this way, we can add more evaluation just by adding a new function, we dont have to worry about score imbalance since everything dynamic

UPDATE:
If you Confuse about \_evaluate_back_opening(). it simply means, "I need either a kitchen or a hallway to have its back clearence, But I prefer kichen to have it rather hallway, so if kitchen does not have back side open, then lock if the hallway have it, if do, give lower mark instead of full mark even though it satisfy the evaluation. "

- Handle divided by 0 issues, It is possible to evaluator to give 0 mark as return

You can use extra helper functions, But you should not keep any code that no longer needed for this, No backward compatibility needed.
