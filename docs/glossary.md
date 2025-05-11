# Glossary

This glossary defines key terms, acronyms, and concepts used within the `ethereum_project` and its documentation.

---

**A**

*   **ADF (Augmented Dickey-Fuller Test):** A statistical test used to check for stationarity in a time series. It tests the null hypothesis that a unit root is present in a time series sample.
*   **ADR (Architectural Decision Record):** A document that captures an important architectural decision made along with its context and consequences.
*   **API (Application Programming Interface):** A set of rules and protocols that allows different software applications to communicate with each other. Used in this project to fetch data from external sources.
*   **ARDL (Autoregressive Distributed Lag Model):** A type of econometric model used for time series data where the dependent variable is regressed on its own lagged values and on current and lagged values of explanatory variables. Useful for variables with mixed orders of integration (I(0) or I(1)).

**B**

*   **Bandit:** A tool designed to find common security issues in Python code.
*   **Black:** An opinionated Python code formatter that ensures consistent code style.

**C**

*   **Cache / Caching:** A mechanism for storing data locally to speed up subsequent requests for the same data, reducing the need to refetch from slow external sources or recompute expensive results. Implemented in `repo://src/utils/cache.py`.
*   **CI/CD (Continuous Integration / Continuous Delivery/Deployment):** A set of practices and tools used to automate the building, testing, and deployment of software. This project uses GitHub Actions for CI.
*   **CLI (Command-Line Interface):** A text-based interface used for interacting with software or operating systems.
*   **CM_API_KEY:** Environment variable for storing a CoinMetrics API key.
*   **Codecov:** An online platform for code coverage reporting and tracking.
*   **CodeQL:** An advanced static analysis engine used for security checking and variant analysis, integrated via GitHub Actions.
*   **Cointegration:** A statistical property of two or more time series variables which indicates that they have a long-run equilibrium relationship, even if they are individually non-stationary. Tested using methods like the Johansen test before fitting a VECM.
*   **Conventional Commits:** A specification for adding human and machine-readable meaning to commit messages.

**D**

*   **DATA_DIR:** Environment variable specifying the root directory for storing raw and processed data files. Defaults to `./data`.
*   **DataFrame:** A two-dimensional, size-mutable, and potentially heterogeneous tabular data structure with labeled axes (rows and columns), provided by the pandas library.
*   **Docker:** A platform for developing, shipping, and running applications in containers.
*   **Dockerfile:** A text document that contains all the commands a user could call on the command line to assemble an image.

**E**

*   **EDA (Exploratory Data Analysis):** The process of analyzing datasets to summarize their main characteristics, often using visual methods and statistical tests. Includes steps like winsorization and stationarity testing in this project.
*   **`.env` file:** A file used in local development to store environment variables, such as API keys. It is gitignored.
*   **ETH (Ethereum):** A decentralized, open-source blockchain with smart contract functionality. The primary subject of valuation in this project.
*   **ETHERSCAN_API_KEY:** Environment variable for storing an Etherscan API key.

**F**

*   **Flake8:** A Python tool that checks code against PEP 8 style guide, programming errors (like `Pyflakes`), and code complexity (`McCabe`).
*   **Fixture (Pytest):** A function that provides a fixed baseline upon which tests can reliably and repeatedly execute. Pytest fixtures are used extensively in `repo://tests/`.

**G**

*   **Git:** A distributed version control system used for tracking changes in source code during software development.
*   **GitHub Actions:** An automation platform integrated with GitHub, used for CI/CD pipelines.

**I**

*   **I(0) (Integrated of order zero):** A time series that is stationary without differencing.
*   **I(1) (Integrated of order one):** A time series that needs to be differenced once to become stationary.
*   **isort:** A Python utility / library to sort imports alphabetically, and automatically separated into sections. (Functionality often covered by Ruff now).

**J**

*   **JSON (JavaScript Object Notation):** A lightweight data-interchange format. `final_results.json` is an output of this project.
*   **Johansen Test:** A statistical test used to determine the number of cointegrating relationships between several non-stationary time series.

**K**

*   **KPSS (Kwiatkowski-Phillips-Schmidt-Shin Test):** A statistical test used to check for stationarity in a time series. It tests the null hypothesis that a time series is stationary around a deterministic trend (level or trend stationary).

**L**

*   **Linting:** The process of running a tool (a linter) that analyzes source code to flag programming errors, bugs, stylistic errors, and suspicious constructs.
*   **Lockfile (`requirements-lock.txt`):** A file that pins the exact versions of all project dependencies (including transitive ones) to ensure reproducible builds.

**M**

*   **main.py (`src/main.py`):** The main entry point script for executing the full end-to-end analysis pipeline.
*   **Markdown (MD):** A lightweight markup language with plain-text-formatting syntax, used for creating formatted text using a plain-text editor.
*   **Mermaid:** A Javascript-based diagramming and charting tool that renders Markdown-inspired text definitions to create and modify diagrams dynamically.
*   **Metcalfe's Law:** A principle that states the effect of a telecommunications network is proportional to the square of the number of connected users of the system (n^2). Often cited in the context of network valuations.
*   **MkDocs:** A fast, simple, and downright gorgeous static site generator that's geared towards building project documentation.
*   **MkDocstrings:** An MkDocs plugin for rendering Python docstrings into documentation pages.
*   **Mocking (`unittest.mock`):** The practice of replacing parts of your system with mock objects during testing to isolate the code under test.
*   **MPLCONFIGDIR:** Environment variable for Matplotlib's configuration/cache directory.
*   **MyPy:** A static type checker for Python.

**N**

*   **NaN (Not a Number):** A special floating-point value representing an undefined or unrepresentable value, often used by pandas for missing data.
*   **NASDAQ:** A major stock market index, used as an external market benchmark in this project.
*   **NumPy:** A fundamental package for scientific computing with Python, providing support for large, multi-dimensional arrays and matrices, along with a large collection of high-level mathematical functions to operate on these arrays.

**O**

*   **OLS (Ordinary Least Squares):** A common statistical method used to estimate the parameters of a linear regression model by minimizing the sum of the squares of the differences between the observed and predicted values.
*   **OOS (Out-of-Sample Validation):** The process of evaluating a model's performance on data that was not used to train or fit the model. This project uses rolling window validation.

**P**

*   **Pandas:** A Python library providing high-performance, easy-to-use data structures and data analysis tools.
*   **Parquet (Apache Parquet):** A columnar storage file format optimized for use with big data processing frameworks. Used in this project for storing DataFrames efficiently.
*   **Pre-commit:** A framework for managing and maintaining multi-language pre-commit hooks. Hooks are run locally before committing code.
*   **Pyarrow:** A Python library that provides a Pythonic interface to Apache Arrow, used for efficient in-memory columnar data processing and interchange, and for reading/writing Parquet files.
*   **Pydantic:** A Python library for data validation and settings management using Python type annotations.
*   **Pytest:** A mature, feature-rich Python testing framework.
*   **Python:** The primary programming language used for this project.

**R**

*   **RapidAPI:** An API marketplace, used in this project as a potential gateway to data sources like CoinMetrics.
*   **RAPIDAPI_KEY:** Environment variable for storing a RapidAPI key.
*   **Requirements Files (`requirements.txt`, `requirements-dev.txt`):** Text files listing project dependencies.
*   **Ruff:** An extremely fast Python linter and formatter, written in Rust. Capable of replacing Flake8, isort, and other tools.

**S**

*   **Safety:** A Python tool that checks installed dependencies for known security vulnerabilities.
*   **SBOM (Software Bill of Materials):** A formal record containing the details and supply chain relationships of various components used in building software.
*   **Scikit-learn:** A machine learning library for Python, used here for utility functions and potentially some preprocessing or validation tasks.
*   **SNAPSHOTS_DIR:** Environment variable specifying the directory for storing snapshots like plots or intermediate model outputs. Defaults to `./snapshots`.
*   **Src (`src/` directory):** The directory containing the core source code of the Python application.
*   **Stationarity:** A key property of time series data, meaning that its statistical properties (like mean, variance, autocorrelation) are all constant over time. Most time series models require data to be stationary or transformed to stationarity.
*   **Statsmodels:** A Python module that provides classes and functions for the estimation of many different statistical models, as well as for conducting statistical tests and statistical data exploration.

**T**

*   **Time Series:** A sequence of data points indexed in time order.
*   **Threat Model:** A structured representation of all the information that affects the security of an application.

**U**

*   **Unit Root:** A feature of some stochastic processes (like random walks) that can cause problems in statistical inference involving time series models. A unit root test (like ADF) is used to check for its presence.

**V**

*   **VECM (Vector Error Correction Model):** A type of vector autoregression (VAR) model designed for use with non-stationary time series that are found to be cointegrated.
*   **Virtual Environment (`.venv`):** An isolated Python environment that allows packages to be installed for use by a particular application, rather than being installed system-wide.

**W**

*   **Winsorization:** A statistical transformation that limits extreme values (outliers) in data to reduce the effect of potentially spurious outliers. Values are set to a specified percentile of the data. 