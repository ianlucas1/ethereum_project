## Executive Summary
The Single-Repo Autonomous Coding Agent is a self-driven development assistant designed to work within one GitHub repository with minimal human oversight. Powered by a single LLM model (configured as `{{PRIMARY_LLM_MODEL_IDENTIFIER}}`), it can plan, implement, and review code changes on its own. The agent continuously iterates through tasks such as fixing bugs, adding features, and updating documentation, all while ensuring code quality via tests, self-reviews, and adherence to established coding best practices. Its autonomy is guided by a strong emphasis on safety: it pauses for human input when environment issues arise or when a code change (especially those altering its own core instructions) needs explicit approval. This autonomy philosophy is about **maximizing automation** in coding tasks while **retaining human control** at crucial decision points.

**Continuous Quality Assurance (North Star):** The agent periodically conducts internal North Star codebase quality assessments. These reviews analyze maintainability, security, testing sufficiency, and adherence to style and philosophy guidelines. The resulting reports are stored internally in `.agent_workspace/quality_reports/` and drive the agent's planning to close any 'Quality Gaps'. Only critical unresolved issues are escalated via `human_requests.md` or a blocked state, so routine review of these internal reports is **not** required from the CEO.

**Agent-Initiated Major Overhauls (RF):** When the agent detects that only a large-scale change can resolve persistent issues or technical obsolescence, it initiates a Refactor & Toolchain Renovation (RF) process. The agent will pause normal tasks to draft a comprehensive proposal for the overhaul (covering rationale, technical plan, and risk mitigation) and await your approval. This proposal comes as a PR for you to review. Once you merge the proposal (signaling approval), the agent proceeds to implement the changes in carefully managed phases, ensuring human oversight on strategic changes.

## Seeding Instructions
To launch the agent, follow these steps to "seed" it using the provided `blueprint_suite.json` specification:
1. **Prepare the Environment:** Ensure you have a suitable environment. Running on macOS within the Cursor IDE is recommended for full integration, but not strictly required. The agent can also operate in a headless command-line environment on macOS or Linux (for example, in CI). In all cases, have Python 3.x installed and any necessary development tools (e.g., compilers, linters) available. Also, provide any required access credentials (like LLM API keys) via environment variables. If the repository contains a Dockerfile or docker-compose setup, you *can* instruct the agent to run all tests inside the container by setting `prefer_docker` to **true** in `agent_config.json`, **or** export `PREFER_DOCKER=true` before running the agent. When neither is set (default), the agent only builds the Docker image on CI **or** when no cached image named `agent_test` exists, speeding up local runs after the first build.
Ensure Docker Desktop (or the Docker CLI) is installed and running if you intend to use containerised tests.
2. **Place the Blueprint:** Make sure `blueprint_suite.json` is present at the root of the repository in Cursor. This file contains the agent's entire design and will be used to generate the agent's codebase.
3. **Initialize Bootstrapping:** In Cursor, use the LLM chat interface or run the bootstrap script to start the agent creation. For example, open the repository in Cursor and instruct the AI (in a system or user prompt) to act as a *Bootstrapper* and execute the plan in `blueprint_suite.json`. If the system has an automated bootstrap mode, run `bootstrap_agent.py` (which reads the blueprint) as the first step.
4. **Generation of Agent Files:** The agent (in bootstrap mode) will read the blueprint and create all specified files and directories (scripts, config files, prompt templates, etc.). Monitor the process in Cursor to ensure files are being created as expected. No manual coding is needed—the blueprint guides the AI to write its own code.
5. **Configuration:** Open `agent_config.json` (created during bootstrapping) and verify the settings. Ensure the `primary_model_identifier` matches your intended model (and you have API access to it). **Note:** If running inside Cursor IDE, the IDE's active model setting may override this value at runtime. In headless mode, the agent will use the configured `primary_model_identifier` for all LLM operations. Check other config fields like `repo_default_branch` and `enable_commit_pushing` for correctness. Add any missing credentials (e.g., set environment variables for API keys if not already set).
6. **Start the Agent:** Run `agent_main.py` using Cursor's execution or a terminal. The agent will begin the INIT-AUDIT phase and proceed autonomously from there, handling planning and coding cycles. Keep `human_requests.md` open to see if the agent logs any immediate needs.
7. **File Context Requests:** After the agent starts, it will often pause at the beginning of an action sequence to request specific file content it needs. These requests are logged (e.g., in a `context-request.json` file or in `human_requests.md`). Provide the requested files by opening them in Cursor or otherwise supplying their content so the agent can resume.

### Quick-start (Headless / CI)

```bash
export OPENAI_API_KEY=sk-…
# Optional: force container usage
export PREFER_DOCKER=true
python bootstrap_agent.py
python agent_main.py --plan

See .github/workflows/agent_headless.yml for a working CI recipe.
```

> **Note 🔧** On the first launch the agent automatically tries to build the Docker image **`agent_test`**.<br>
If that build fails, it pauses in the `Blocked-EnvironmentConfig` state and logs details to `logs/environment.log`.<br>
To skip container use entirely, set **`prefer_docker=false`** in `agent_config.json` (or export `PREFER_DOCKER=false`).

### Key Configuration Flags

| Field           | Purpose                                                                                                                                                                                                                            | Default |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `prefer_docker` | Force the agent to build & run tests inside the repo's Docker container whenever Dockerfiles are present. When **false**, the agent skips a rebuild if an image named `agent_test` already exists and is running outside CI. | `false` |

## Standard Session/Task Initiation Procedure

Whenever you start a new autonomous agent session (or resume a halted session), use the prompt below to initialize the agent:

You are the Autonomous Coding Agent, continuing your mission.
Your operational state is persisted in `.agent_workspace/session_bootstrap.json`.
Your accumulated knowledge is in `.agent_workspace/experiential_knowledge_base/`.
Your core instructions and blueprint are defined by the `blueprint_suite.json` used for your generation.

Load your state, consult your knowledge, and determine your next action according to your operational plan.
Then, request any specific file context you require for that immediate action.
Proceed.

## CEO-Level Intervention Guide
Think of the human operator as a CEO: overseeing high-level direction without micromanaging. The agent is built to handle day-to-day coding autonomously. **Intervene only when necessary:**
- **When the Agent Requests Help:** Pay attention to the `human_requests.md` file and any pull requests the agent opens. If the agent enters a blocked state (e.g., `Blocked-EnvironmentConfig`, `Blocked-AwaitingFileContext`, `Blocked-AwaitingHumanPRApproval`, or `Blocked-AwaitingMetaIntervention`), it will log the reason. Address these items promptly (e.g., provide missing configuration, supply the requested file(s), or review and approve the PR). For example, if a dependency is missing, the agent might attempt an automatic installation; if it fails or requires permissions, you should manually install the dependency or provide access so the agent can continue.
- **When the Agent Needs File Context:** If the agent enters a `Blocked-AwaitingFileContext` state or explicitly requests file content, respond quickly. Check `human_requests.md` or the agent's context request file for the names of files needed, and open or provide those files in the IDE. The agent will remain paused until the required files are supplied.
- **When the Agent Escalates an Issue:** If the agent repeatedly fails to solve a problem, it may enter a `Blocked-AwaitingMetaIntervention` state. In this case, it will log a comprehensive request for meta-level help in `human_requests.md`. Treat this like a call for higher-level intervention: review the details the agent provided (its deep research prompt) to understand the issue, then step in to investigate or bring additional expertise. Once you have a solution or guidance, update the agent's context or code and let it proceed.
- **Critical Decisions or Strategy Changes:** If you see the agent consistently tackling low-priority tasks or veering off course project-wise, you may step in to reprioritize. This can be done by creating an issue or note in the repository for the agent to find during its Planning phase, effectively guiding its next objectives.
- **Review Core Changes:** The agent will not merge changes to its own core instructions (e.g., its blueprint, prompt templates, or internal guidance documents) without human approval. When such a self-revision PR appears, review it carefully. Ensure that the proposed changes improve the agent and do not introduce risks or remove essential safeguards. Approve the PR only if you are confident in the change.
- **Review Major Initiative Proposals:** If the agent opens a PR containing a Major Initiative Proposal (for an extensive refactor or toolchain upgrade), review it thoroughly. This document outlines a broad plan; ensure the goals are justified and the approach is sound. You may request changes or clarifications via PR comments. Merge (approve) the proposal only when you are confident in its feasibility and alignment with strategic objectives. The agent will not proceed with the overhaul without your approval.
- **Minimal Tweaks:** Avoid modifying the agent's generated code or prompts yourself unless absolutely necessary. Unanticipated manual changes could confuse the agent's context. Instead, if something is wrong, let the agent diagnose and fix it via its self-revision capability or by hinting through feedback in `human_requests.md` or an issue.

## Overseeing Major Agent-Driven Initiatives (RF)

**What Are RF Initiatives?** RF (Refactor & Toolchain Renovation) initiatives are agent-proposed major overhauls. These are larger in scope than regular tasks, aiming to address fundamental codebase improvements or major dependency updates in one coordinated effort.

**How the Agent Proposes RF:** The agent monitors its performance and codebase health. It may identify the need for an RF initiative when it encounters:
- Persistent quality issues flagged repeatedly in North Star quality reports (indicating that minor fixes won't suffice)
- Recurring "Lessons Learned" entries pointing to the same underlying architectural weakness
- Critical dependencies or tools in the project that are deprecated or far outdated, requiring significant upgrade
- A direct directive from you (the CEO), such as an issue labeled **#MAJOR_INITIATIVE_PROPOSAL** instructing the agent to consider a big overhaul

When such conditions arise, the agent will enter a special planning mode to draft a **Major Initiative Proposal**. This proposal is a structured Markdown document (named with a `PROPOSAL-RF-...` convention) that outlines the plan in detail: the justification and goals, scope of changes, technical approach, impact analysis, risk assessment, a phase-by-phase execution plan, testing strategy, and rollback considerations. The agent will open this proposal as a pull request for you to review, and it will **pause its routine work** (entering a blocked state awaiting your decision).

**CEO Review and Approval:** Your role is to evaluate the Major Initiative Proposal PR much like you would a high-level project plan. Ensure that the reasons for the overhaul are sound and that the proposed solution and execution plan make sense. If you have concerns or suggestions, you can comment on the PR and even close it if you decide not to proceed. If you agree with the plan, merge the PR to approve it. Merging signals the agent that it can proceed with the initiative. (Until the PR is merged, the agent will remain in the blocked awaiting approval state and not make any large-scale changes.)

**Phased Execution without Micromanagement:** Once approved, the agent moves into executing the plan. It will create new branches and PRs for each phase of the initiative as outlined in the proposal (using the RF ID in branch names for clarity). The agent handles each phase autonomously: implementing the planned changes, running tests, and performing self-reviews. After each phase, it might produce a brief debrief or progress update (documented in the repository or `human_requests.md`) to keep a record of how the initiative is going. You do not need to intervene during these phases unless an unexpected issue arises that the agent cannot handle (in which case it will pause and alert you, similar to other blocked states).

**Post-Initiative Validation:** After all phases are completed, the agent enters a final validation step. It will run a full test suite and possibly generate a fresh codebase quality report to ensure the initiative's goals were achieved and no regressions were introduced. Once everything looks good, the agent concludes the RF initiative (marking it as completed in its logs) and resumes normal operation, picking up regular tasks again. The entire process is logged and traceable (via the proposal document, phase pull requests, and updates in the agent's state), so you can always audit what was done. RF initiatives thus allow the agent to evolve the project in significant ways while keeping you informed and in control at the key approval point.

## Monitoring and Emergency Stop
Even though the agent is autonomous, you should monitor its activity, especially early on:
- **Logging and Progress:** Keep an eye on the `logs/` directory (if available) or the console output in Cursor while the agent runs. The agent's log will detail state transitions and actions. Regularly check `human_requests.md` for any new entries. Additionally, watch the repository's commit history and open pull requests for a quick sense of changes being made.
- **Relic File Quarantine:** During the initial audit (and occasionally later), the agent may identify "relic" files in the repository (e.g., leftover artifacts from a previous run or extraneous files). Instead of deleting them, the agent will isolate these files (moving them to a safe location or updating `.gitignore` to ignore them) so they don't interfere. Rest assured, no file is permanently removed; quarantined relics remain available for your review later. You can decide whether to reintegrate, archive, or delete these files at a later time, but their immediate isolation helps maintain a clean working context for the agent.
- **Emergency Stop:** If you observe the agent behaving erratically, making harmful changes, or stuck in a problematic loop, you can intervene to stop it. This might involve killing the agent's process or using a special shutdown command if available. Since the agent regularly saves state, you can later resume operation once any issues are resolved, and it will pick up from the last stable state.

## Session Completion and Final Status Messages
Even when running autonomously, the agent will signal the end of its session (or task cycle) with a final status message written to `human_requests.md`. This message will indicate whether it finished its tasks successfully, encountered an issue that caused it to halt, or is simply awaiting further instructions (idle). Upon completion, you can review the repository for the latest changes, run any final tests or audits you see fit, and then decide on next steps (such as continuing development or shutting down the agent). If the agent halted due to an error, inspect the logs and any human_requests.md entries to diagnose the problem before restarting or concluding the session.
