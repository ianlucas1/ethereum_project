# ---- Builder Stage ----
# This stage installs all dependencies, including development tools,
# and copies all source code. It can be used for comprehensive testing
# or as a source for the final runtime image.
FROM python:3.12-slim AS builder
LABEL stage=builder

WORKDIR /app

# Copy all relevant requirements files
# These files are expected in the build context (project root).
COPY requirements.txt requirements-dev.txt ./
COPY requirements-lock.txt ./
# This will copy the requirements-runtime-lock.txt you just generated.
COPY requirements-runtime-lock.txt ./

# Install all dependencies from the main lock file (includes dev tools)
RUN pip install --no-cache-dir --upgrade pip \
 && if [ -f requirements-lock.txt ]; then \
       echo "Builder: Installing all dependencies from requirements-lock.txt"; \
       pip install --no-cache-dir -r requirements-lock.txt; \
    elif [ -f requirements-dev.txt ]; then \
       echo "Builder: Warning - requirements-lock.txt not found. Falling back to requirements-dev.txt."; \
       pip install --no-cache-dir -r requirements-dev.txt; \
    else \
       echo "Builder: Error - No suitable development requirements file found (requirements-lock.txt or requirements-dev.txt)." && exit 1; \
    fi

# Copy the rest of the application source code, respecting .dockerignore
COPY . .

# (Optional) Add any build steps here if your project has them
# e.g., RUN python setup.py build_ext --inplace

# ---- Final Stage ----
# This stage creates a lean production image with only runtime dependencies.
FROM python:3.12-slim AS final

# Set environment variables for Python, pip, and runtime configurations
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Placeholder for RAPIDAPI_KEY, should be set at runtime via -e or orchestration
    RAPIDAPI_KEY=dummy \
    # Set a writable directory for Matplotlib's configuration/cache
    MPLCONFIGDIR=/app/matplotlib_cache

WORKDIR /app

# Create a non-root user 'app' and group 'app'
RUN groupadd -r app && useradd --no-log-init -r -g app -s /sbin/nologin -c "Docker image user" app

# Copy runtime requirement files from the build context.
COPY requirements.txt ./
COPY requirements-runtime-lock.txt ./

# Install only runtime dependencies using the runtime-specific lock file.
RUN pip install --no-cache-dir --upgrade pip \
 && if [ -f requirements-runtime-lock.txt ]; then \
       echo "Final: Installing runtime dependencies from requirements-runtime-lock.txt"; \
       pip install --no-cache-dir -r requirements-runtime-lock.txt; \
    elif [ -f requirements.txt ]; then \
       echo "Final: Warning - requirements-runtime-lock.txt not found. Falling back to requirements.txt."; \
       pip install --no-cache-dir -r requirements.txt; \
    else \
       echo "Final: Error - No runtime requirements file found (requirements.txt or requirements-runtime-lock.txt)." && exit 1; \
    fi \
# Clean up. Removing requirement files after installation keeps the image lean.
 && rm -rf /tmp/* /var/tmp/* ~/.cache/pip \
 && rm -f requirements.txt requirements-runtime-lock.txt

# Copy necessary application code from the builder stage.
# --chown=app:app sets the correct ownership for the non-root user.
COPY --from=builder --chown=app:app /app/src ./src
COPY --from=builder --chown=app:app /app/main.py .
# If PROJECT_CONFIG_DETAILS.md or other specific files are read by the app at runtime:
# COPY --from=builder --chown=app:app /app/PROJECT_CONFIG_DETAILS.md .
# If you have other assets like data files needed at runtime, copy them:
# COPY --from=builder --chown=app:app /app/data_for_runtime ./data_for_runtime

# Create and set permissions for data and snapshot directories
RUN mkdir -p /app/data /app/snapshots /app/matplotlib_cache \
 && chown -R app:app /app/data /app/snapshots /app/matplotlib_cache


# Switch to the non-root user
USER app

# Define the command to run the application
CMD ["python", "main.py"]# trigger build
