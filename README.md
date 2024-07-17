# ESGF-Playground
A playground or sandbox for developing the new ESGF event stream based publisher.

This docker compose stac provides a full suite for simulating the ESGF publishing flow.

## Stack Description

This docker compose stack provides a simulation of:

- The central ESGF event stream (Kafka)
- The central ESGF ingestion API 
- A STAC based "Code Node" (simulating CEDA's ESGF STAC service)
- A STAC based "Secondary Node" (simulating an ESGF note interested only in the CMIP "historical" experiment)
- A CLI for producing simulated CMIP and CORDEX data and sending it to the ingest API.

## Further Work

- Simulate a second "Core Node" (approximating Globus)
- Provide an ingest API per simulated ESGF Core Node 
- Provide Update and Revoke functionality
- Move to ESGF or CEDA repository
- Publish images to docker hub (ESGF account)
- Provide Helm charts
- Fix loging on the ingest API
- Fully document
- Improve CLI functionality
- Move common modules and models to a shared library on pypi

## Basic Use

```console
docker compose up
```

To print a STAC record to the screen:

```console
cd esgf-generator
poetry install
poetrt run esgf_generator
```

### Kakfa UI

Go to http://localhost:8080 (the UI for KAFKA) and register and account with username `admin@admin.io` and password 
`admin`, then log in with those credentials.

This UI provides a complete view of the stage of your Kafka service and is described here https://www.conduktor.io/console/.

### STAC Browser

A STAC browser simulating a **core** ESGF index is available at http://localhost:9011. This service should be listening 
to all the publication, retraction and update events in the Kafka queue.

A STAC browser simulating a **secondary** ESGF index is also available at http://localhost:9013. This service is 
only listening to certain event in the Kafka queue.


