# Software Bill of Materials (SBOM)

<!-- TODO: SME to provide details on SBOM generation and contents if a formal, machine-readable SBOM (e.g., CycloneDX, SPDX) is required.
Consider integrating a standard SBOM generation tool into the CI/CD pipeline.
-->

This project's Python dependencies are meticulously tracked and managed via lockfiles, which serve as a human-readable and machine-parseable list of components and their exact versions.

## Dependency Lockfiles

*   **`repo://requirements-lock.txt`**: This file pins the versions for *all* Python dependencies, including both runtime and development packages, along with their transitive dependencies. It ensures fully reproducible environments for local development and Continuous Integration (CI) builds.
*   **`repo://requirements-runtime-lock.txt`**: This file pins the versions for *only runtime* Python dependencies and their transitive dependencies. It is specifically used for building the lean, production-focused Docker image, ensuring that only necessary packages are included.

## Source of Dependencies

These lockfiles are generated using `pip-tools` (specifically the `pip-compile` command) based on the following primary requirement files:

*   **`repo://requirements.txt`**: Defines the core runtime Python dependencies with generally flexible version specifiers (e.g., `pandas~=2.2`).
*   **`repo://requirements-dev.txt`**: Defines development-specific Python dependencies, such as testing frameworks, linters, and formatters.

## Lockfile Integrity

The consistency and up-to-dateness of `requirements-lock.txt` (relative to `requirements.txt` and `requirements-dev.txt` if combined for generation) and `requirements-runtime-lock.txt` (relative to `requirements.txt`) are crucial. The `repo://.github/workflows/lockfile-check.yml` workflow in the CI pipeline helps ensure that committed lockfiles accurately reflect the specified dependencies.

## Viewing Dependencies

To view the list of installed packages and their versions in your local environment (after installing from a lockfile), you can use:

```bash
pip list
```

For a more structured view, you can inspect the contents of the lockfiles directly. They are designed to be human-readable. 