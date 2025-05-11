# CI/CD Pipeline Overview

The `ethereum_project` leverages GitHub Actions for its Continuous Integration and Continuous Delivery (CI/CD) pipeline. This automates testing, quality checks, security scans, and other processes. The pre-commit framework complements this by running checks locally before code is even pushed.

```mermaid
graph LR
    subgraph Developer Workflow
        direction LR
        Dev[Developer Commits Code Locally] -- Uses --> Hooks[Pre-commit Hooks<br><pre>.pre-commit-config.yaml</pre><br>Ruff, Black, Flake8, MyPy, Bandit, Codespell]
        Hooks -- Feedback --> Dev
        Dev -- Pushes to GitHub / Opens PR --> GitHub[GitHub Repository]
    end

    subgraph GitHub Actions CI/CD [Automated CI/CD on GitHub]
        direction TB
        GitHub -- Triggers on Push/PR/Schedule --> MainCI[Main CI<br><pre>ci.yml</pre><br>Build, Pytest, Coverage (Codecov), Basic Security (Bandit, Safety)]
        GitHub -- Triggers on Push/PR/Schedule --> CodeQL[CodeQL Analysis<br><pre>codeql.yml</pre><br>Advanced Static Security Analysis]
        GitHub -- Triggers on Push/PR --> PythonCI[Python CI<br><pre>python-ci.yml</pre><br>Parallel Pytest, Caching]
        GitHub -- Triggers on Push/PR --> DockerBuild[Docker Build Test<br><pre>docker-build.yml</pre><br>Validates Dockerfile]
        GitHub -- Triggers on Schedule --> NightlyAudit[Nightly Audit<br><pre>nightly_audit.yml</pre><br>Runs <pre>scripts/qa_audit.py</pre>, Commits Scoreboard]
        GitHub -- Triggers on Push/PR --> LockfileCheck[Lockfile Check<br><pre>lockfile-check.yml</pre><br>Ensures <pre>requirements-lock.txt</pre> Consistency]
        GitHub -- Triggers on Push/PR/Schedule --> StaticSecurity[Static Security<br><pre>static-security.yml</pre><br>Focused Bandit & Safety Scans]
        GitHub -- Triggers on Schedule --> NightlyMatrix[Python Nightly Full Matrix<br><pre>python-nightly-full-matrix.yml</pre><br>Multi-OS Pytest (Ubuntu, Windows, macOS)]
    end

    MainCI --> R_Coverage[Coverage Report to Codecov.io]
    MainCI --> R_TestResults[Test Pass/Fail Status]
    CodeQL --> R_CodeQLAlerts[Security Alerts in GitHub]
    PythonCI --> R_TestResults2[Test Pass/Fail Status]
    DockerBuild --> R_DockerStatus[Build Image Success/Failure]
    NightlyAudit -- Commits --> GitHub
    LockfileCheck --> R_LockfileStatus[Consistency Pass/Fail Status]
    StaticSecurity --> R_SecurityAlerts[Security Alerts in GitHub]
    NightlyMatrix --> R_TestResults3[Multi-OS Test Pass/Fail Status]

    style Dev fill:#lightblue
    style Hooks fill:#lightgreen
    style GitHub fill:#grey
```

Key aspects illustrated:
*   **Local Development Loop:** Developers use pre-commit hooks for immediate feedback on code style, linting, and basic security.
*   **GitHub Actions Triggering:** Pushes, Pull Requests, and scheduled events trigger various workflows.
*   **Comprehensive Checks:** The CI pipeline includes unit testing, code coverage, static security analysis (Bandit, Safety, CodeQL), Docker build validation, lockfile consistency, and nightly audits.
*   **Feedback Mechanisms:** Results are reported via GitHub checks, Codecov, and direct commits from audit scripts.

For a detailed breakdown of each workflow, refer to `repo://docs/ci/pipeline.md`. 