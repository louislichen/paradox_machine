# Motivation

This part has already been clearly explained in [intro](./intro.md), so it will not be repeated here.

# Problems Description

1. Collecting Evidence:
How to gather broad and relevant evidence before conducting a detailed analysis.

2. Paradox Expansion:
How to clearly define the scope and boundaries of a problem, and explore multiple possible outcomes in a comprehensive manner.

3. Paradox Detection and Mitigation:
How to examine the process in full, identify paradoxes by considering multiple possible outcomes, and propose appropriate mitigation or resolution strategies.

# Solutions v0.1.0

Since we are building a Minimum Viable Product (MVP), the core solution relies on **Structured Prompt Chaining**. The goal is to force the LLM out of its default "helpful and agreeable" state and into a strict, objective formal logic evaluator.

We address the three problems outlined above through a three-phase logical pipeline:

**1. Phase I: Premise Extraction & Axiomatization**

In this MVP phase, "Evidence" comes from the agent's internal knowledge base. The agent does not just parse the user's text; it actively retrieves relevant domain knowledge to contextualize the input.

- **Action:** The agent analyzes the user input and cross-references it with its pre-trained internal knowledge to identify gaps between "what is said" and "what works in reality."

- **Output Structure:**

    - **Variables:** What are the independent and dependent variables?
    
    - **Stated Goal:** What is the explicit objective?
    
    - **Hidden Assumptions:** What unstated conditions must be true for this viewpoint to hold? The agent leverages its internal knowledge to uncover these prerequisites (e.g., "This assumes network latency is zero," or "This assumes infinite processing power").
    
**2. Phase II: Multi-Dimensional Expansion**

This phase employs a constrained Tree of Thoughts (ToT) approach.

- **Action:** The agent calculates the outcomes of specific logical branches.

- **Algorithmic Triggers:**

    - **Extremification:** What happens if the input variable is pushed to infinity ($X \to \infty$) or zero ($X \to 0$)?
    
    - **Inversion:** What happens if the opposite of the premise is enforced?
    
    - **Time Scaling:** If this rule is applied iteratively for $N$ cycles, does the system stabilize or collapse?

**3. Phase III: Contradiction Catching & Mitigation**

This is the "Critic" phase. The agent compares the outcomes generated in Phase II against the Stated Goals from Phase I to see if a logical closed loop of self-destruction has occurred.

- **Action:** The agent acts as a strict referee to detect paradoxes and categorize them.

- **Detection Protocol:**

    - If Goal $X$ logically necessitates the destruction of Goal $X$ $\implies$ Antinomy (System Bug / Self-Contradiction).
    
    - If Goal $X$ appears to work but relies on a flawed Hidden Assumption $\implies$ Falsidical Paradox (Hidden Fallacy).
    
    - If Goal $X$ works, but results in a highly counterintuitive state that is technically valid $\implies$ Veridical Paradox (Standard System Trade-off).

**4. Expected Output: The Paradox Report**

To ensure objectivity, the Agent will generate a structured report:

REPORT ID: [Hash]

**1. LOGICAL BREAKDOWN**

- Primary Goal: [Goal]

- Core Variables: [A, B, C]

**2. STRESS TEST RESULTS (Phase II)**

- Branch A: Result...

- Branch B: Result...

**3. PARADOX DIAGNOSIS (Phase III)**

- Type: [Antinomy / Falsidical / Veridical]

- Reasoning: Since [Goal] leads to [Outcome], a contradiction arises because...

**4. SUGGESTED MITIGATION**

[Actionable Suggestion]