FROM python:3.12-slim

RUN mkdir -p /opt/esgf-consumer
WORKDIR /opt/esgf-consumer

COPY . /opt/esgf-consumer

RUN pip install poetry

RUN poetry install --only main

ENTRYPOINT ["sh", "-c", "poetry run python $SCRIPT"]