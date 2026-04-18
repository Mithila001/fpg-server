at `app/algorithms/fpg_rooms/fpg_post_process/post_processor.py` We should significantly modify the current post processing logics. And should update the API respond accordingly.
this will be a significant change from existing process.

- Only Keep the Wall Union Process and remove rest.
- Remove all room type called `verandaoutdoorspace`

Final data structure should be like this 
```
"union_walls" : [],
"rooms":{
    "<roomName>":{
        "room_name":,
        "room_type":,
        "room_walls":[]
    },
"doors":[
    {
        "room1_name" : <OpeningConnectedRoom1Name>
        "room1_type" : <OpeningConnectedRoom1Type>,
        "room2_name" : <OpeningConnectedRoom2Name>,
        "room2_type" : <OpeningConnectedRoom2Type>,
        "opening_type" : ,
        "x1": ,
        "y1": ,
        "x2": ,
        "y2": ,
    }, .... 
]
"windows":[
    {
        "room_name" : <WindowConnectedRoom1Name>
        "room_type" : <WindowConnectedRoom1Type>,
        "opening_type" : ,
        "x1": ,
        "y1": ,
        "x2": ,
        "y2": ,
    }, ....
    ]
}
```
Here, all windows can have default type `default_window` for now.

With this modification, now the process is much simpler.
