### Chapter 4.2.3 Optuna

The project utilizes Optuna, an open-source autonomous optimization framework, to generate Hint Points for the floor plan solver. Optuna serves as a high-performance black-box optimization engine, capable of exploring continuous, discrete, and conditional search spaces while employing 'pruning' to terminate unpromising trials early.

At its core, the system utilizes the Tree-structured Parzen Estimator (TPE) sampler to intelligently navigate the search space. By implementing Optuna, the project gains a feedback-driven optimization loop; the framework learns from the solver's previous layout attempts to suggest increasingly effective hint points, ensuring the solver converges on a valid and optimized floor plan efficiently.

Initially , the System use Optuna to Sample Directly to CP-SAT solver generation with room dimentions. But due to a single solver generation + post process + score takes 10-15 seconds of time, causing less that 50 trial able to run within desired 120 seconds. Optuna Required to run at least 100 trials see the "learning" happens.

Due to this, The Whole Floor Plan generation change with to a new flow. The System Instead of Optuna Trialing for Solver Variables directly, Optuna Modified to Sample Solver Hint points. Only High scored hints point will be eligible to use for Solver Hint. <`Here I believe my explanation lacks the clarity, improve it`> This Implementation let the system to able to run 200-800 trial to get better floor plan hints.

The Optuna Use Low Resolution Search Space Since the Sampling is focus on building a graph like layout. Low Resolution Search space is appropriate due to hint requiring having space between each point and reducing the search space and improve solver performance. <`Explain this Scaling Down Feature More accurately`>
<`Explain What are the Sampling Parameters Roughly`>

<`Describe What Trial Returns`>

<`Explain the Sampler Behavior, But only focus on what actually the project use and befit from `>

The Project Default turned off Persistent storage feature due sampler focus on various sampling requirement rather fixed one.
<`Only explain pruning if it actually use in the project actively, I think it does ont even though the code is there `>

<`Keep in mind some of the code in Optuna Implementation is not being actively use right now, So do not talk about them in the project`>
