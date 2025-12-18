ARG PYTHON_ENV=python:3.10-slim

FROM $PYTHON_ENV as build
# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

RUN apt-get update && \
    apt-get install --yes --no-install-recommends curl g++ libopencv-dev && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app
WORKDIR /app

COPY pyproject.toml poetry.lock ./

# Install pip-tools and generate requirements from poetry.lock
RUN pip install --no-cache-dir pip-tools toml && \
    python -c "import toml; d=toml.load('pyproject.toml'); deps=d['tool']['poetry']['dependencies']; print('\\n'.join(f'{k}=={v}' if isinstance(v,str) and v[0].isdigit() else k for k,v in deps.items() if k!='python'))" > requirements.in && \
    pip-compile requirements.in -o requirements.txt --resolver=backtracking && \
    pip install --no-cache-dir -r requirements.txt

FROM $PYTHON_ENV as prod

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True
# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./
COPY magic-pdf.json /root

COPY --from=build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=build /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=build /usr/local/bin/magic-pdf /usr/local/bin/magic-pdf
COPY --from=build /usr/local/bin/uvicorn /usr/local/bin/uvicorn

RUN python download_models.py

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]
