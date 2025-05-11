# Configuration Reference

This document outlines the configuration options for the `ethereum_project`, primarily managed through environment variables. The application uses `pydantic-settings` to load and validate these settings, as defined in `repo://src/config.py`.

## Environment Variables

Environment variables are the primary way to configure the application. They can be set directly in your shell or, for local development, placed in a `.env` file in the project root. The `.env` file is automatically loaded if it exists.

| Variable            | Default Value (in code) | Required | Description                                                                                                |
| ------------------- | ----------------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| `RAPIDAPI_KEY`      | `None`                  | **Yes**  | Your API key for RapidAPI, used as a proxy for various data sources like CoinMetrics.                        |
| `CM_API_KEY`        | `None`                  | No       | Your direct CoinMetrics API key, if you choose to use CoinMetrics directly instead of via RapidAPI.          |
| `ETHERSCAN_API_KEY` | `None`                  | No       | Your Etherscan API key. Currently noted as optional and potentially not used by the core pipeline.           |
| `DATA_DIR`          | `./data`                | No       | Path to the directory where raw and processed data files (e.g., Parquet) are stored and read from.           |
| `SNAPSHOTS_DIR`     | `./snapshots`           | No       | Path to the directory for storing snapshots (e.g., model outputs, intermediate results for debugging).     |
| `LOG_LEVEL`         | `INFO`                  | No       | Logging level for the application (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`).                               |
| `MPLCONFIGDIR`      | (Set in Dockerfile)     | No       | Writable directory for Matplotlib's configuration/cache. Primarily relevant for Dockerized execution.        |
| `PYTHONUNBUFFERED`  | (Set in Dockerfile)     | No       | If set to `1`, ensures Python output is sent straight to terminal without buffering. Useful in Docker.     |
| `PYTHONDONTWRITEBYTECODE` | (Set in Dockerfile) | No       | If set to `1`, prevents Python from writing `.pyc` files. Useful in Docker.                               |

**Note on `DATA_DIR` and `SNAPSHOTS_DIR`**:
If these directories do not exist, the application will attempt to create them at startup.
The default paths (`./data`, `./snapshots`) are relative to the project root where the script is executed.

### Example `.env` File:

```dotenv
# Required:
RAPIDAPI_KEY="your_actual_rapidapi_key_here"

# Optional:
# CM_API_KEY="your_coinmetrics_api_key_here"
# ETHERSCAN_API_KEY="your_etherscan_api_key_here"
# DATA_DIR="./my_custom_data"
# SNAPSHOTS_DIR="./my_custom_snapshots"
# LOG_LEVEL="DEBUG"
```
Ensure this `.env` file is in your `repo://.gitignore`.

## Command-Line Arguments

*   **`src/main.py`**:
    *   Currently, `src/main.py` does not explicitly define or parse command-line arguments for its core pipeline execution. Configuration is handled via environment variables.

*   **Utility Scripts (in `repo://scripts/`)**:
    *   `scripts/qa_audit.py`:
        *   `--mode`: Specifies the audit mode (e.g., `full`). Example from CI: `python scripts/qa_audit.py --mode=full`.
        *   *(Other arguments might exist; refer to the script's help message or source code for details.)*
    *   Other scripts in `scripts/` may have their own CLI arguments. It's best to check their source code or run them with a `--help` flag if available.

## Key Configuration Files

While environment variables handle dynamic settings, several files configure development tools and project behavior:

*   **`repo://.pre-commit-config.yaml`**: Configures pre-commit hooks for linters, formatters, etc.
*   **`repo://mypy.ini`**: Configuration for the MyPy static type checker.
*   **`repo://pyproject.toml`**: Project metadata and tool configuration (e.g., Ruff linter settings).
*   **`repo://Dockerfile`**: Defines the Docker build, including environment variables set within the container.
*   **`repo://.github/workflows/`**: YAML files in this directory configure CI/CD pipelines, which may also define or use environment variables specific to those workflows.

For detailed contents and explanations of many of these configuration files, you can also refer to `repo://PROJECT_CONFIG_DETAILS.md`. 