# Architectural Decision Records (ADRs)

This section contains Architectural Decision Records (ADRs) for the `ethereum_project`. ADRs document important architectural decisions, their context, and consequences.

We use a lightweight ADR format based on [Michael Nygard's template](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions).

## ADR Log

*   [ADR 0000: Use Markdown Architectural Decision Records](0000-use-markdown-architectural-decision-records.md)
*   [ADR 0001: Implement Caching for API Calls and Expensive Computations using Decorator](0001-caching-decorator.md)

<!-- TODO: Add more ADRs as significant architectural decisions are made. -->

## Creating a New ADR

1.  Copy `docs/adr/template.md` to `docs/adr/NNNN-short-title.md`, where `NNNN` is the next sequential number.
2.  Fill in the ADR sections: Title, Status, Context, Decision, Consequences.
3.  Keep it concise and focused on a single decision.
4.  Update this index file with a link to the new ADR. 