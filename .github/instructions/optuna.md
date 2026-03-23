look at #file:algorithm_manager.py , Do you see i am calling #sym:RunFPG  under #sym:DEV_RUN ? 
But when i use optuna, what should i let optuna call #sym:DEV_RUN  or just #sym:RunFPG ?

I know providing just #sym:DEV_RUN  is not correct, optuna need values to ajust. So i am thinkgin when #sym:DEV_RUN  calls, and construct the #sym:requirements  and instaded of sending to #sym:RunFPG , we send to optuna function, where optuna change values of #sym:requirements  and call #sym:RunFPG  how many time it wants.

How about this ? Am i correct or wrong? OR is there better way




#file