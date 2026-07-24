# Server Side Event Streaming Feature Implementation

Here we need a clean and proper setup to implement the SSE logic.
Then we need to cleanly feature to call this to send even to client in more scalable, friendly way.
Here the footprint of the SSE calling should be very little as possible.

When comes to SSE.
Each SSE should have a tag to group the events
there should be a throttling feature when sending streaming can be throttle with config values.
Example: if the throttle is 500ms, and there are SSE send per each 100ms, only 0ms,100,200,300,400,500ms messages are sended. rest did not sent. This is filtered with tags, mean if the 0ms is tag A and 40ms is tag B and 90ms is tag A, then  both 0ms and 40ms event is sended And 90ms is throttled and did not send dues to tag A differed is less than 100ms

This setup is still in discuses mode. need to evaluate the realistic and pragmatic points

We need a Consist SSE structure type as well

What to Call in SSE

- Each Candidate Search Trial Results (Hint Point Only)
- Each 

