# ADR 0000: Use Markdown Architectural Decision Records

*   **Status**: Accepted
*   **Date**: 2024-07-28
*   **Deciders**: Project Maintainers

## Context and Problem Statement

As the `ethereum_project` evolves, we need a consistent and lightweight way to document significant architectural decisions. These decisions often have long-term implications for the project's structure, maintainability, and development. Without a clear record, the rationale behind past decisions can be lost, leading to repeated discussions or a misunderstanding of the system's design.

## Decision Drivers

*   **Clarity:** Provide a clear understanding of why the system is built the way it is.
*   **Consistency:** Ensure a uniform way of recording architectural decisions.
*   **Accessibility:** Make decisions easily accessible to all team members, including new joiners.
*   **Lightweight Process:** Avoid overly bureaucratic documentation processes.
*   **Version Control:** Keep decision records version-controlled alongside the codebase.

## Considered Options

1.  **Wiki Pages (e.g., GitHub Wiki):**
    *   Pros: Easy to edit, good for collaborative content.
    *   Cons: Can become detached from the codebase, harder to version control in sync with code changes, discoverability can be an issue.
2.  **Documents in a Shared Drive (e.g., Google Docs):**
    *   Pros: Rich editing features.
    *   Cons: Detached from codebase, version control is separate, access management can be complex.
3.  **Markdown Files in the Repository (ADRs):**
    *   Pros: Stored with the code, version controlled, easily reviewable in pull requests, plain text format is future-proof, can be rendered nicely by documentation generators like MkDocs.
    *   Cons: May require a specific structure/template to maintain consistency.
4.  **No Formal Documentation:** Rely on code comments and tribal knowledge.
    *   Pros: Minimal effort.
    *   Cons: Not scalable, knowledge is easily lost, difficult for new contributors.

## Decision Outcome

Chosen option: **Markdown Files in the Repository (ADRs)**.

We will use a lightweight format for ADRs, stored as Markdown files in the `docs/adr/` directory. A template (`docs/adr/template.md`) will be provided to guide the creation of new ADRs. An index of ADRs (`docs/adr/index.md`) will be maintained.

The format will be based on Michael Nygard's ADR template, focusing on:
*   Title (with a sequential number)
*   Status (Proposed, Accepted, Rejected, Superseded)
*   Date
*   Context and Problem Statement
*   Decision Drivers (optional but recommended)
*   Considered Options
*   Decision Outcome (with rationale)
*   Consequences (positive, negative, trade-offs)

## Consequences

### Positive Consequences

*   Architectural decisions will be documented clearly and consistently.
*   Rationale for decisions will be preserved.
*   New team members can get up to speed more quickly on architectural history.
*   ADRs can be reviewed as part of the code review process if they accompany a PR.
*   Easy integration with the MkDocs documentation site.

### Negative Consequences

*   Requires discipline from the team to create and maintain ADRs for significant decisions.
*   ADRs might become outdated if not actively reviewed, though being in the repo helps.

This approach provides a good balance between formality and agility for documenting the architectural evolution of the project. 