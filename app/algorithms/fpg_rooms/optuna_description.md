# Optuna Usage in Floor Plan Generation

This project uses Optuna to tune parameters for the floor plan generation flow. The goal is to test different configuration values in an automatic search and identify those that produce the best aggregated floor plan score. The process evaluates complete designs end to end and keeps track of how changes affect the quality of outcomes.

Using Optuna here means running many candidate trials, each with a slightly different setup, and letting the optimizer compare their performance. It is applied to the same building/layout problem, helping the system learn the most effective parameter settings for consistent, high-quality layout generation.