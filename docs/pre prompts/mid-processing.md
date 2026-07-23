
IN the project, I we have Pre Processing and Post processing feature. I also want a mid processing layer as well (can use appropriate name if the 'mid process' is not ideal)

Here this layer should able to interfere with the mid flow and modify content from almost all the place. For initial work, this is what i want.


During the Candidate Search -> Candidate Score flow. We need to interfere between and get the hint points. Then for the available rooms hint points. we need to do this.
Have predefine palings like this
Veranda -> Living ROom
Living Room -> Bedroom (this should happen for all bedrooms)
Living Room -> Kitchen
Living Room -> Dining ROom
Garage -> Living Room
Kitchen -> Dining Room
All Bedrooms to All Bathroom (many to many)
... And more paths adding later

Do this patting calculate where from point A to point B can go through hallway points, living room.

And After all these shortest path calculation, Find the hallway potions that did not crossed any time and mark them
Then remove those points before sending the data to Candidate Score section like nothing happen.  Mean candidate score doesn't know if the flow is gotten interrupted.

This is just one idea, and if there are flow interruption need to be done, this is the layer that do it.


