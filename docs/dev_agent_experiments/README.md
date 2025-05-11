# Autonomous Development Agent Experiments

────────────────────────────────────────────────────────
## Context-Hygiene Rules  (Agent MUST follow)

1. **Progressive summarisation**  
   • After each numbered experiment, write a ≤ 5-line “Mini-Summary” at the end of your `github_cli_execution_log.md` entry.  
   • Do **not** copy full CLI/stdout into chat; save it in the log only.

2. **Chunked logging**  
   • For multi-screen outputs, fence them in the log and reference them by section (“see log §Exp 3-11 → Bandit output”).  
   • Chat should carry only high-level reasoning.

3. **Critical reminder scratchpad**  
   Before executing commands, append this to your private scratchpad (not the repo):  
   > **Reminder**: `main` is protected → never push directly.  

4. **Token guard (no hard pause)**  
   • If chat context nears overflow, write a 1-paragraph recap in the log and **continue**; do **not** halt at 4 000 tokens.  
   • Aim to keep active chat ≤ 2 000 tokens by summarising old reasoning.

5. **Read-first contract**  
   *Before taking any action*, you must read & absorb:  
   1. `github_cli_plan.md` (roadmap & experiment IDs)  
   2. `github_cli_execution_log.md` (latest history)  
   3. `README.md` (this file)  

6. **Time-boxing rule**  
   Each experiment gets **≤ 20 minutes or ≤ 3 failed attempts**.  
   Exceeding this means: log attempts, mark “Partially Complete”, move on.

Failure to follow these rules counts as an experiment failure.
────────────────────────────────────────────────────────

## Purpose of these Experiments

This directory houses records and plans related to the "side quest" of enabling a frontier-level reasoning Large Language Model (LLM), like the one currently interacting with you, to operate as an increasingly autonomous development agent. The primary goal is to allow the LLM to further the development and refinement of the `ethereum_project` codebase, operating within the Cursor IDE.

These experiments are designed to:
- Systematically test and document the LLM agent's capabilities, particularly concerning Git version control, GitHub CLI (`gh`) interactions, and general shell command execution.
- Identify current limitations, points of confusion, or areas where the agent's understanding or tooling access is insufficient.
- Refine the agent's strategies for interacting with the development environment and managing common coding workflows.
- Explore the requirements for an LLM to make autonomous decisions, such as merging pull requests, in a scenario where it is the sole "reviewer".

The ultimate aim is to improve the agent's effectiveness and reduce the need for human intervention for routine development tasks.

## How to Use These Documents (For a Future LLM Instance)

If you are an LLM instance picking up this work, welcome! Please familiarize yourself with the following:

1.  **This `README.md` file:** It provides the overarching context.
2.  **`github_cli_plan.md`:** This file contains the detailed, structured plan for experiments specifically focused on the GitHub CLI. It outlines tests that have been devised but may not have all been executed yet.
3.  **`github_cli_execution_log.md`:** This is a critical file. It contains a chronological log of experiments performed, including:
    *   The agent's reasoning *before* taking an action (Chain of Thought - CoT).
    *   The exact command(s) executed.
    *   The raw output from those commands.
    *   The agent's analysis and interpretation of the results *after* the action (Post-Action CoT).
    *   Specific learnings, reflections, or newly identified questions.

To continue the work:
- Review the `github_cli_plan.md` to understand pending experiments.
- Review the `github_cli_execution_log.md` to see what has been accomplished, what issues were encountered, and the latest state of understanding.
- Continue executing planned experiments or devise new ones based on previous findings, always maintaining the logging format in `github_cli_execution_log.md`.

## Collaboration with Human User (You!)

A key aspect of these experiments is collaboration. The LLM agent operates within a specific environment (Cursor IDE, specific shell setup) which may have its own nuances.

**Crucially, if the agent documents in the `github_cli_execution_log.md` that it was unable to obtain expected results from a CLI command or API query (e.g., due to output parsing issues, unexpected errors, or apparent environmental differences), it will explicitly request you, the human collaborator, to:**
1.  Run the *exact same command* in your own terminal environment (e.g., Cursor's built-in terminal or your system terminal).
2.  Provide the complete, raw output back to the agent via the chat interface.

This collaborative troubleshooting is vital for distinguishing between the agent's inherent limitations and environmental factors, and for finding workarounds. Your assistance in these cases is invaluable for the progress of this experimental "side quest". 