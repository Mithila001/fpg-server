Here what I want you to do is Remove Unnecessary/Unused Features From the Project. To Clean up the project. Since this project is more like Research project, there are some codes,features that implemented, but later discarded/ignored. So now what i want is to only keep the code that use for main flow and remove rest. I created a dedicate branch for this so we can be more ease with code delete.

IMPORTED: DO NOT READ `/docs` folder. that container lot of unnecessary document. And Do not Read `/test` Folder Content As well. Those test are bloated. Dont waist your time on there

Its being few months since I last work with this project so i dont remember everything. But I will provide some information that I remembered that could be helpful for you with this task.

I place all complex logic with app\algorithms folder and keep the rest of the project as Generic Server. Some for the features in the app\algorithms are not being used right now and can be removed.

Check the types folders, I remember that was one palace i kind of mixed up when come to clean organization. Some code might be dead code there.

In my project, there are two flows. Buildable Space Finding Flow and Floor Plan generation Flow.

The Main Orchestrator file is app\services\algorithm_manager_v2.py and app\services\buildable_space_manager.py. Look at the code in here and you can easily identify the entire project flow and what and what not being used.

In This project, Database is not a Main Character, it was mostly for few data storage.

Ok, those are the info i remembered. Use those info your help. And create a solid plan or simplifying this
