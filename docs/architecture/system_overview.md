# System Overview

The following diagram provides a high-level overview of the `ethereum_project` components and their interactions.

```mermaid
graph TD
    A[External Data Sources APIs<br>(e.g., CoinMetrics via RapidAPI, Yahoo Finance)] --> B(Data Fetching Module<br><pre>src/data_fetching.py</pre><br>Handles API calls, caching);
    B --> C{Raw Data Storage<br><pre>data/raw/</pre><br>(Parquet files)};
    C --> D(Data Processing Module<br><pre>src/data_processing.py</pre><br>Cleans, merges, transforms, resamples);
    D --> E{Processed Data Storage<br><pre>data/processed/*.parquet</pre><br>(Daily & Monthly datasets)};
    E --> F(Exploratory Data Analysis (EDA)<br><pre>src/eda.py</pre><br>Winsorization, Stationarity Tests);
    F --> G(Econometric Modeling<br><pre>src/ols_models.py</pre><pre>src/ts_models.py</pre><br>OLS, VECM, ARDL);
    G --> H(Model Diagnostics<br><pre>src/diagnostics.py</pre><br>Residual Analysis, Structural Breaks);
    G --> I(Out-of-Sample Validation<br><pre>src/validation.py</pre><br>Rolling Window Validation);
    H --> J(Reporting Module<br><pre>src/reporting.py</pre><br>Generates JSON results & summary);
    I --> J;
    J --> K[Output Artifacts<br><pre>data/final_results.json</pre><br>Console Summary, Plots];

    subgraph Execution & Orchestration
        direction LR
        U[User/Developer]
        M[Main Pipeline Script<br><pre>src/main.py</pre>]
        R[Interactive Research<br><pre>research.py</pre>]
    end

    U --> M;
    U --> R;
    M --> B; M --> D; M --> F; M --> G; M --> H; M --> I; M --> J;


    subgraph Environment & Automation
        direction TB
        Dock[Docker Environment<br><pre>Dockerfile</pre>]
        CI[CI/CD Pipeline<br><pre>.github/workflows/</pre>]
        Hooks[Pre-commit Hooks<br><pre>.pre-commit-config.yaml</pre>]
    end

    Dock --> M;
    CI --> M; # (CI runs tests and can execute main script)
    Hooks -- Affects --> U; # (Local dev workflow)

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#f9f,stroke:#333,stroke-width:2px
    style J fill:#f9f,stroke:#333,stroke-width:2px
    style M fill:#ccf,stroke:#333,stroke-width:2px
```

This diagram illustrates the flow from external data sources, through data fetching and processing stages, into modeling, validation, and finally reporting. It also shows the role of Docker for containerized execution and CI/CD for automation. 