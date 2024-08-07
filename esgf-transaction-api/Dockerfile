FROM python:3.12-slim

RUN mkdir -p /opt/esgf-transaction-api
WORKDIR /opt/esgf-transaction-api

COPY . /opt/esgf-transaction-api

RUN pip install poetry

RUN poetry install --only main

ENTRYPOINT ["poetry", "run", "uvicorn", "esgf_transaction_api.main:app", "--host", "0.0.0.0"]