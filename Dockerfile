####
# ethereum_project – runtime image
# 4.3.1  Dockerfile (Python 3.12-slim, non-root)
####
FROM python:3.12-slim

# create an unprivileged user
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# placeholder so pytest can import settings without a real secret
ENV RAPIDAPI_KEY=dummy

# install Python dependencies first (leverages Docker layer caching)
# This installs all dependencies from requirements-lock.txt, including
# development tools. This is for convenience and to ensure the testing
# environment within Docker matches the development setup closely.
# For a smaller production image, consider a multi-stage build
# or separate runtime-only requirements.
COPY requirements*.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && if [ -f requirements-lock.txt ]; then pip install --no-cache-dir -r requirements-lock.txt ; \
    elif [ -f requirements.txt ];       then pip install --no-cache-dir -r requirements.txt      ; fi

# copy project source
COPY . .

# drop privileges for runtime
USER app

CMD ["python", "main.py"] 