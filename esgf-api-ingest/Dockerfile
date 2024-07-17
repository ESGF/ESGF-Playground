FROM python:3.12-slim

RUN mkdir -p /opt/esgf-api-ingest
WORKDIR /opt/esgf-api-ingest

COPY . /opt/esgf-api-ingest

RUN pip install poetry

RUN poetry install

ENTRYPOINT ["poetry", "run", "uvicorn", "esgf_api_ingest.main:app", "--host", "0.0.0.0"]