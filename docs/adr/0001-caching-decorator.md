# ADR 0001: Implement Caching for API Calls and Expensive Computations using Decorator

*   **Status**: Accepted
*   **Date**: 2024-07-28
*   **Deciders**: Project Maintainers

## Context and Problem Statement

The `ethereum_project` relies on fetching data from external APIs (e.g., CoinMetrics via RapidAPI, Yahoo Finance) as managed by `repo://src/data_fetching.py`. These API calls can be:
1.  **Slow:** Network latency and API response times can significantly increase the overall pipeline execution time.
2.  **Rate-Limited:** Frequent calls might hit API rate limits, disrupting data collection.
3.  **Costly:** Some APIs may have usage-based pricing.
Additionally, certain data processing steps or computations within the pipeline might be resource-intensive and produce consistent results for the same inputs. Repeatedly executing these can be inefficient.

We need a mechanism to cache the results of these operations to improve performance, reduce external dependencies during runs, and minimize API costs/rate limit issues.

## Decision Drivers

*   **Performance:** Reduce overall pipeline execution time.
*   **Cost Efficiency:** Minimize API call costs.
*   **Reliability:** Reduce failures due to API rate limits or temporary network issues.
*   **Developer Experience:** Allow faster iterations during development and testing by using cached data.
*   **Reusability:** Provide a generic caching solution applicable to various functions.

## Considered Options

1.  **Manual Caching Logic within Each Function:**
    *   Each function that needs caching would implement its own logic to check for existing results (e.g., in a file) and save new results.
    *   Pros: Fine-grained control per function.
    *   Cons: Highly repetitive, error-prone, difficult to maintain consistency, clutters business logic.
2.  **Centralized Caching Service/Manager:**
    *   A dedicated class or module that functions explicitly call to get/set cached items.
    *   Pros: Centralized logic, easier to manage cache policies globally.
    *   Cons: Requires modifying function signatures or bodies to interact with the caching service, slightly more verbose than a decorator.
3.  **Decorator-Based Caching (`@cache_to_disk`):**
    *   A Python decorator that wraps functions needing caching. The decorator handles cache lookup, saving results, and argument hashing.
    *   Pros: Unobtrusive (minimal changes to function code), reusable, encapsulates caching logic cleanly, Pythonic.
    *   Cons: Hashing complex or unhashable arguments can be tricky (requires careful implementation), magic can sometimes make debugging harder if not well understood.
4.  **Using an External Caching Library (e.g., `diskcache`, `joblib.Memory`):**
    *   Leverage existing, well-tested libraries.
    *   Pros: Robust, feature-rich (e.g., expiry, size limits, different backends).
    *   Cons: Adds an external dependency, might be overkill if requirements are simple, need to ensure it integrates well with pandas DataFrames (e.g., efficient serialization).

## Decision Outcome

Chosen option: **Decorator-Based Caching (`@cache_to_disk`) implemented in `repo://src/utils/cache.py`**.

We will implement a custom caching decorator primarily targeting functions that return pandas DataFrames or other serializable Python objects.
*   **Mechanism:**
    *   The decorator will create a unique cache key based on the function's qualified name and a hash of its arguments' serialized representation. Special handling will be needed for pandas DataFrames as arguments (e.g., hash based on content or a subset of metadata).
    *   Results will be serialized to disk. For pandas DataFrames, Parquet is preferred for efficiency. For other objects, pickle might be used, or JSON if simple.
    *   The cache will be stored in a configurable directory (e.g., `data/cache/` or `snapshots/cache/`).
*   **Features:**
    *   Basic time-based expiry (e.g., "cache valid for 24 hours").
    *   Option for forced refresh (e.g., an argument to the decorator or a global flag).
    *   Logging of cache hits and misses.
*   **Rationale:** This approach offers a good balance of reusability, unobtrusiveness, and control over the caching logic, especially for handling pandas DataFrames efficiently. While external libraries are powerful, a targeted custom decorator allows precise control over serialization (crucial for DataFrames) and avoids adding a new major dependency if the core needs are met. The logic already prototyped in `src/utils/cache.py` can be formalized based on this.

## Consequences

### Positive Consequences

*   Significant reduction in execution time for repeated pipeline runs, especially the data fetching stages.
*   Reduced load on external APIs, mitigating rate limiting and potential costs.
*   Improved developer productivity due to faster feedback loops.
*   Ability to run the pipeline partially offline if data is cached.
*   Cleaner function code as caching logic is abstracted away.

### Negative Consequences

*   **Cache Invalidation Complexity:** Ensuring the cache is properly invalidated when underlying data sources change or function logic is updated requires careful consideration (expiry and forced refresh help mitigate this).
*   **Argument Hashing:** Reliably hashing complex or mutable arguments (e.g., DataFrames, custom objects) can be challenging and may require custom serialization or hashing strategies within the decorator.
*   **Disk Space Usage:** Caching large DataFrames can consume significant disk space. A mechanism for clearing or pruning the cache might be needed in the future.
*   **Debugging:** If caching behaves unexpectedly, it might add a layer of complexity to debugging. Clear logging is important.

This decision is foundational to making the data pipeline efficient and robust. The implementation can be found in `repo://src/utils/cache.py` and its usage in `repo://src/data_fetching.py`. 