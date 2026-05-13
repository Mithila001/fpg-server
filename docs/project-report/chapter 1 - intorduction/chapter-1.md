# Introduction

## 1.1 Overview

The project developed a residential floor plan generation platform centered on a server-side computational engine. Its purpose is to transform a client’s conceptual requirements—such as room composition, approximate room sizes, and site dimensions—into a layout that satisfies architectural constraints and local regulatory expectations. Rather than treating floor planning as a purely aesthetic exercise, the system treats feasibility, legality, and spatial coherence as primary conditions. The resulting workflow therefore functions as an automated mediator between informal design intent and structured architectural output.

An accompanying client-facing web application was also developed to support this process. It provides the interactive environment through which users define plots, submit requests, monitor job progress, and review returned plans. However, the principal computational contribution of the project lies in the server-side generation pipeline, where constraint reasoning, optimization, and geometric refinement are performed. For that reason, this report places greater emphasis on the backend architecture than on the presentation layer.

## Problem Statement

In Sri Lankan residential practice, private landowners often begin with sketches that do not yet satisfy setback rules, circulation allowances, or minimum room dimensions. These sketches must then be redrawn repeatedly before they can support professional evaluation. The difficulty is not limited to regulatory compliance. Users also face the burden of manually drafting multiple dimensionally accurate alternatives in order to compare layouts and test whether a chosen arrangement is practical within the available land. This iterative sketching process is slow, error-prone, and inaccessible to non-specialists.

Existing automated floor plan tools often intensify this problem because they prioritize visually appealing compositions while underemphasizing hard spatial constraints. As a result, generated plans may appear plausible but remain unsuitable for professional use. The project therefore addresses a double inefficiency: the time spent manually redrawing alternative plans and the subsequent effort required by architects to correct non-compliant proposals.

## Proposed Solution

To reduce these inefficiencies, the project introduced a digital planning assistant that converts user requirements into a feasible layout through a staged computational workflow. The system operates as a sequence of dependent transformations rather than a single monolithic generator. It first determines an appropriate buildable envelope, then searches for a valid arrangement of rooms within that envelope, and finally refines the geometry so that the output is more coherent and presentable.

The overall pipeline includes the following conceptual stages:

- **Buildable-space estimation:** the site boundary is interpreted together with setback and access assumptions to determine the usable planning area.
- **Constraint-based synthesis:** a solver-driven core searches for room placements that satisfy dimensional and relational rules.
- **Guided layout discovery:** a preliminary sampling stage helps steer the search toward promising room configurations before the heavier optimization stage is executed.
- **Geometric refinement:** the initial layout is cleaned, aligned, and adjusted to improve plan clarity and structural consistency.
- **Opening placement:** doors, windows, and related exposure points are generated to complete the architectural representation.

Together, these stages reduce the amount of manual drafting required from the user and provide a more reliable bridge between a rough design idea and a reviewable floor plan.

## 1.2 Background

In the Sri Lankan context, residential design must reconcile personal preference with municipal and national building control. The practical challenge is to represent these rules early enough that a proposed arrangement remains feasible rather than being corrected only after drafting is complete. The project was framed within that need. Its contribution is not merely regulatory checking, but the reduction of repetitive redrawing and dimension adjustment that normally precedes an architect’s first meaningful review.

By inserting computation between the user’s rough idea and the formal design stage, the system shortens the path from intent to reviewable plan. This is especially valuable for household projects in which clients frequently explore several alternatives before settling on a preferred arrangement. The platform therefore supports both compliance and iteration: it helps users avoid infeasible concepts early while also reducing the effort needed to compare multiple layout options.

## 1.3 Objectives

The project aimed to achieve several specific technical and functional objectives:

- **Provide a web-based interface:** create an interactive environment for entering land data, defining room requirements, and reviewing generated layouts.
- **Calculate usable buildable space:** determine the maximum practical footprint under site constraints, setbacks, and access-related assumptions.
- **Generate feasible room arrangements:** use constraint reasoning and guided optimization to produce floor plans that satisfy functional and spatial requirements.
- **Improve geometric quality:** refine the raw output so that rooms align more consistently and the final plan is easier to interpret.
- **Support regulatory plausibility:** ensure that generated layouts remain compatible with basic residential planning requirements, including room sizing and ventilation-related considerations.
- **Enable responsive interaction:** provide asynchronous job handling so that users can submit requests, track progress, and receive results without blocking the interface.

## 1.4 Deliverables

The following primary deliverables were produced as part of the project:

- **Backend API:** a Python-based server that implements the generation pipeline, job management, and geometric post-processing.
- **Client-facing web application:** an interactive interface that communicates with the server, submits floor plan requests, and presents results to users.
- **Exportable floor plan output:** structured plan data that can be reviewed, visualized, and reused in downstream workflows.
- **Asynchronous job workflow:** a request-and-status model that allows users to monitor long-running generation tasks through the interface.

## 1.5 Scope and Limitations

The project scope was intentionally focused on single-story residential buildings in order to keep the core spatial logic reliable and computationally manageable.

- **Included:** support for two-dimensional floor plan generation, convex land parcels, automated opening placement, and visual plan output suitable for client review.
- **Excluded:** multi-story structures, detailed electrical and plumbing layouts, structural engineering analysis, and fully detailed construction documentation.

## Reviewer Notes

- The chapter now emphasizes the repetitive manual redrawing burden in addition to regulatory compliance, which better reflects the practical motivation of the project.
- The client-facing application is described as a supporting component, while the report remains centered on the server-side generation engine where the main technical contribution resides.
- The scope section was normalized as part of Chapter 1 rather than left as a later-section numbering fragment.
