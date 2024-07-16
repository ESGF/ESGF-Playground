FROM python:3.12-slim

RUN mkdir -p /opt/esgf-consumer
WORKDIR /opt/esgf-consumer

COPY . /opt/esgf-consumer

RUN pip install poetry

RUN poetry install

ENTRYPOINT ["poetry", "run", "esgf_kafka_consumer"]