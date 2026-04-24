# Abstract

promptukit is a source-based authoring layer that turns reusable engineering code into checked assessment items and worked lecture examples. Instructors author learning artifacts as plain-text source files that call domain libraries such as parasolpy for parameter generation, solution computation, visualization, or validation. During the build process, promptukit executes these checks before rendering the final materials, making answer-key validation part of the same workflow that produces the artifact.

# State of the Field

## Online assessment platforms

PrairieLearn, WeBWorK, Moodle, etc.

They are good at: delivery, grading, randomization, course management

But they are not primarily designed as a **local authoring layer** around reusable engineering domain packages.

## Domain-specific engineering software

Examples include parasolpy in your case, plus hydrology, optimization, simulation, or data-analysis packages more generally.

They are good at: computation, domain modeling, reusable code

But they do not directly provide: assessment item structure, answer-key rendering, learning-objective metadata

## Ad-hoc notebooks and scripts

These are good at fast local experimentation, but they do not share a consistent source format, a reproducible build process, and artifact packaging. This is especially problematic if students lose access to the learning management system after graduation. 

# Contribution

promptukit is a source-based authoring layer that turns reusable engineering code into checked assessment items and worked lecture examples. We implement features from paid ecosystems but in a local, open source format that allows future collaborators to add functionality and use within their own codebases.

