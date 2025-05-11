# Installation and Setup Guide

This guide provides detailed instructions for setting up the `ethereum_project` for local development and execution.

## Prerequisites

*   **Python:** Python 3.12 is required.
    *   It's recommended to manage Python versions using a tool like `pyenv`. The `repo://.python-version` file in the project root specifies `3.12`, so `pyenv` will automatically use this version if installed and configured.
*   **Git:** For cloning the repository and managing versions.
*   **Operating System:** While development primarily occurs on macOS/Linux, the project aims for cross-platform compatibility (Windows is tested in nightly CI).

## 1. Clone the Repository

If you haven't already, clone the project repository from GitHub:

```bash
git clone https://github.com/ianlucas1/ethereum_project.git
cd ethereum_project
```

## 2. Set Up Python Virtual Environment

It is crucial to use a Python virtual environment to isolate project dependencies and avoid conflicts with system-wide packages.

```bash
# Ensure you are using Python 3.12
# If using pyenv, it will automatically pick up Python 3.12 from .python-version
python3.12 -m venv .venv
```

Activate the virtual environment:

*   **On macOS/Linux:**
    ```bash
    source .venv/bin/activate
    ```
*   **On Windows (PowerShell):**
    ```powershell
    .\.venv\Scripts\Activate.ps1
    ```
    (If script execution is disabled, you might need to run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` first.)
*   **On Windows (Command Prompt):**
    ```bash
    .\.venv\Scripts\activate.bat
    ```

Your command prompt should now indicate that you are in the `.venv` environment.
Ensure the `.venv/` directory is listed in your `repo://.gitignore` file.

## 3. Install Dependencies

The project uses `pip-tools` to manage dependencies, with exact versions pinned in lockfiles for reproducibility.

1.  **Upgrade pip (optional, but good practice):**
    ```bash
    python -m pip install --upgrade pip
    ```

2.  **Install all dependencies (Runtime + Development):**
    `repo://requirements-lock.txt` contains all pinned dependencies required for development, testing, and running the application.
    ```bash
    pip install -r requirements-lock.txt
    ```
    This is the recommended approach for developers.

    If you only need to run the application and do not intend to run tests or linters, you could install only runtime dependencies:
    ```bash
    # For minimal runtime-only setup (not for development)
    # pip install -r requirements-runtime-lock.txt
    ```

## 4. Environment Variables (`.env` file)

The application requires API keys and can be configured via environment variables. These are loaded from a `.env` file in the project root using `python-dotenv`.

1.  **Create a `.env` file in the project root:**
    ```bash
    touch .env
    ```

2.  **Add your API keys and any other necessary configurations.**
    At a minimum, `RAPIDAPI_KEY` is required for the primary data fetching. Refer to `repo://docs/reference/config.md` for a full list of environment variables.

    Example `.env` content:
    ```dotenv
    # Required:
    RAPIDAPI_KEY=your_actual_rapidapi_key_here

    # Optional (depending on data sources enabled/used):
    # CM_API_KEY=your_coinmetrics_api_key_here
    # ETHERSCAN_API_KEY=your_etherscan_api_key_here

    # You can override default data directory if needed:
    # DATA_DIR=./custom_data_location
    ```

**Important Security Note:** The `.env` file should **never** be committed to Git. Ensure it is listed in your `repo://.gitignore` file.

## 5. Set Up Pre-commit Hooks (Recommended for Developers)

This project uses `pre-commit` hooks to automatically run linters, formatters, and other checks before each commit. This helps maintain code quality and consistency.

1.  **Install pre-commit hooks into your local Git repository:**
    ```bash
    pre-commit install
    ```

Now, the configured hooks (see `repo://.pre-commit-config.yaml`) will run automatically when you `git commit`.

You can also run all hooks on all files manually at any time:
```bash
pre-commit run --all-files
```

## Next Steps

With the project set up, you can now:

*   Run the full analysis pipeline: `python src/main.py` (see `repo://docs/tutorials/01-first-run.md`)
*   Explore data interactively using `repo://research.py`.
*   Run tests: `pytest` (see `repo://docs/quality/testing.md`)

Welcome to the project! 