# Appendix: Server-Sent Event Communication in the Planning Workflow

The thesis already explains the generation logic; this appendix summarizes the communication layer that makes the process observable and recoverable. Server-Sent Events are used as a low-latency, one-way channel from server to client, complementing request submission and periodic status polling. Once a job is accepted, the client opens a stream tied to the job reference and session identity. The stream carries compact JSON messages that report progress, intermediate candidates, and terminal outcomes without repeated full-page requests.

| Phase                  | Typical meaning                                   | Client handling                                   |
| ---------------------- | ------------------------------------------------- | ------------------------------------------------- |
| Submission and start   | Job accepted, worker launched                     | Store the job reference and open the event stream |
| Early progress         | Initial synthesis and feasibility checks          | Update the progress indicator and preview         |
| Candidate evaluation   | Better layouts may replace earlier ones           | Keep the best validated result visible            |
| Refinement and cleanup | Geometry is normalized and openings are finalized | Refresh rendered shapes and labels                |
| Terminal states        | Success, manual cancellation, or timeout          | Close the stream and finalize the interface       |

    A common event path is: job accepted → initialization → draft layout → refinement passes → geometric cleanup → scoring → best-candidate updates → final success or termination. If the algorithm produces several improving candidates, only the strongest validated result is retained for presentation, which reduces visual noise and prevents the interface from oscillating between inferior layouts.

Termination follows three principal routes. First, a valid completion emits a final success event and returns the result payload. Second, manual cancellation interrupts the worker and marks the job as terminated. Third, a timeout watchdog stops jobs that exceed the allowed duration. When a credible intermediate solution already exists at timeout, the system may return that best solution instead of an empty failure state; otherwise, it returns a timeout outcome with no floor plan.

The stream is therefore not merely a progress meter. It is a traceable control surface that supports responsiveness, interruption recovery, and clear separation between asynchronous computation and presentation.

## Reviewer Notes

- The appendix focuses on communication and lifecycle behavior only, not on the planning algorithm itself.
- Timeout behavior is described in its two valid forms: best-result preservation or explicit timeout failure.
