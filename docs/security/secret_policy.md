# Secret Handling Policy

This document outlines the policy for managing secrets, such as API keys and sensitive configuration data, within the `ethereum_project`. The primary goal is to prevent accidental exposure of secrets in the codebase or version control system.

## Core Principles

1.  **No Secrets in Version Control:** Secrets must never be committed to the Git repository, whether in source code, configuration files, or documentation.
2.  **Environment Variables for Configuration:** Secrets and sensitive configurations should be supplied to the application via environment variables.
3.  **Principle of Least Privilege:** API keys and access tokens should be configured with the minimum necessary permissions required for the application's functionality.
4.  **Secure Storage for CI/CD:** Secrets required by Continuous Integration / Continuous Delivery (CI/CD) pipelines must be stored using the secure secret management features of the CI/CD platform (e.g., GitHub Actions Encrypted Secrets).

## Local Development

*   **`.env` File:** For local development, secrets are managed using a `.env` file located in the project root.
    *   This file should be created manually by each developer.
    *   The `.env` file **must** be listed in `repo://.gitignore` to prevent accidental commits.
    *   The application (`repo://src/config.py`) uses the `python-dotenv` library to automatically load variables from this file into the environment when the application starts.
*   **Example `.env` content:**
    ```dotenv
    RAPIDAPI_KEY="your_local_development_rapidapi_key"
    # Other sensitive variables
    ```

## Dockerized Execution

*   When running the application via Docker, secrets should be passed as environment variables to the `docker run` command (e.g., using the `-e` flag or `--env-file` option).
    ```bash
    docker run --rm -e RAPIDAPI_KEY="your_runtime_rapidapi_key" ethereum_project
    ```
*   The `repo://Dockerfile` may define placeholder or dummy values for secrets (e.g., `RAPIDAPI_KEY=dummy`), but these should not be functional keys and must be overridden at runtime for actual operation.

## Continuous Integration / Continuous Delivery (CI/CD)

*   **GitHub Actions Secrets:** Secrets required by GitHub Actions workflows (e.g., `CODECOV_TOKEN` for uploading coverage reports) are stored as Encrypted Secrets at the repository or organization level.
    *   These secrets are accessed in workflow files using the `${{ secrets.SECRET_NAME }}` syntax (e.g., `${{ secrets.CODECOV_TOKEN }}` in `repo://.github/workflows/ci.yml`).
*   **API Keys in CI:** For workflows that need to run the main application pipeline (e.g., integration tests or specific nightly jobs that perform data fetching), API keys like `RAPIDAPI_KEY` should also be configured as GitHub Secrets. Workflows might use placeholder values for non-sensitive runs (e.g., `RAPIDAPI_KEY: "ci-placeholder"` as seen in `repo://.github/workflows/ci.yml` for unit tests that mock external calls).

## Review and Auditing

*   Regularly review code (especially changes to configuration loading or CI/CD workflows) to ensure no secrets are inadvertently exposed.
*   Periodically audit active API keys and their permissions.
*   Rotate API keys if a compromise is suspected or as part of a regular security schedule.

## Reporting a Security Vulnerability

If you discover a security vulnerability, including exposed secrets, please refer to the guidelines in `repo://SECURITY.md`.

This policy aims to protect sensitive information integral to the operation and security of the `ethereum_project`. All contributors are expected to adhere to these guidelines. 