# ESGF-Playground
A playground or sandbox for developing the new ESGF event stream based publisher.

This docker compose stac provides a full suite for simulating the ESGF publishing flow.

## Stack Description

This docker compose stack provides a simulation of:

- The central ESGF event stream (Kafka)
- A STAC based "East Node" (simulating CEDA's ESGF STAC service)
- A STAC based "West Node" (simulating Globus's ESGF STAC service)
- A STAC based "Secondary Node" (simulating an ESGF note interested only in the CMIP "historical" experiment)
- A CLI for producing simulated CMIP and CORDEX data and sending it to the ingest API of either node

## Configuration

The playground is currently configured to split publication events into particular topics. Each topic is defined as 
a string in the form `<mip_era>.<experiment_id>.<source_id>`, for example:

- CMIP6.historical.CMCC-ESM2

This allows easy filtering of topics based on the MIP, the experiment, or the source of the data. This in tern allows 
simulation of nodes interested only in data form a set of institutions, or a particular experiment. 

To change this structure, change the functionality of the function `get_topic` in the `esgf-api-ingest` package. Topics 
are created on the fly as can the configuration for which topics are listened to (see below). 

Most configuration options are available through the file `docker-compose.yml`. For instance, the 
**secondary** node is configured to listen only to messages regarding the `historical` experiment. This is achieved 
through a regular expression in the `KAFKA_TOPICS` environment variable:

```yaml
  stac-consumer-secondary: 
    build:
      context: esgf-consumer
      dockerfile: Dockerfile
    environment:
      CONSUMER_GROUP: "secondary-node"
      BOOTSTRAP_SERVERS : '["kafka1:19092"]'
      KAFKA_TOPICS: '.*\.historical\..*'
      STAC_SERVER: "http://app-elasticsearch-secondary:8080"
    depends_on:
      kafka1:
        condition: service_healthy
```

## Generating Simulation Data

A utility for creating fake records is available as follows:

```console
foo@bar:~$ cd esgf-generator
foo@bar:~$ poetry install
foo@bar:~$ poetry run esgf_generator --help
Usage: esgf_generator [OPTIONS] COUNT

  Generate a number of ESGF items.

  COUNT is the number of items to generate.

Options:
  --node [east|west]
  --publish / --no-publish  Whether to publish items to ESGF, or just print to
                            the console (print happens anyway). Default: --no-
                            publish
  --delay / --no-delay      Add a random sub-second delay between publishing
                            items to ESGF. Default: --no-delay
  --help                    Show this message and exit.

foo@bar:~$ poetry run esgf_generator 1 --no-publish --node east
Producing 1 STAC records
{
  "bbox": [
    -101.68525075626562,
    -71.20920887444608,
    84.34962991832455,
    74.12980403236749
  ],
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [
          -101.68525075626562,
          -71.20920887444608
        ],
        [
          84.34962991832455,
          -71.20920887444608
        ],
        [
          84.34962991832455,
          74.12980403236749
        ],
        [
          -101.68525075626562,
          74.12980403236749
        ],
        [
          -101.68525075626562,
          -71.20920887444608
        ]
      ]
    ]
  },
  "properties": {
    "title": "xrjifVTiUPlByzQFQJYr",
    "description": null,
    "datetime": "2340-05-17T13:09:54.568699Z",
    "created": null,
    "updated": "1986-08-02T04:20:13.615253Z",
    "start_datetime": null,
    "end_datetime": null,
    "license": "JYxRlTjnJfrkaAhkmPOo",
    "providers": [
      {
        "name": "513",
        "description": null,
        "roles": [
          "ehtHJBlhlSnzfuBFEEKP"
        ],
        "url": "VjjVeqvdMUHQBkaelhCC"
      }
    ],
    "platform": null,
    "instruments": [
      "STcsFTkYFmlgDODQznAT"
    ],
    "constellation": "mSqEvCaHHHNEFvkGSdlu",
    "mission": null,
    "gsd": 7.211943115584001,
    "citation_url": "http://cera-www.dkrz.de/WDCC/meta/CMIP6/CMIP6.CMIP.NOAA-GFDL.HadGEM3-GC31-LL.ssp585.r1i1p1f1.day.rsus.gr.v20220101.json",
    "variable_long_name": "Eastward Near-Surface Wind",
    "variable_units": "W m-2",
    "cf_standard_name": "surface_downwelling_longwave_flux_in_air",
    "activity_id": "CMIP",
    "data_specs_version": "01.00.31",
    "experiment_title": "update of RCP4.5 based on SSP2",
    "frequency": "mon",
    "further_info_url": "https://furtherinfo.es-doc.org/CMIP6.CMIP.NOAA-GFDL.HadGEM3-GC31-LL.ssp585.r1i1p1f1.day.rsus.gr.v20220101",
    "grid": "gn",
    "grid_label": "gr",
    "institution_id": "NOAA-GFDL",
    "mip_era": "CMIP6",
    "source_id": "HadGEM3-GC31-LL",
    "source_type": "AOGCM AER BGC CHEM",
    "experiment_id": "ssp585",
    "sub_experiment_id": "none",
    "nominal_resolution": "100 km",
    "table_id": "day",
    "variable_id": "rsus",
    "variant_label": "r1i1p1f1",
    "instance_id": "CMIP6.CMIP.NOAA-GFDL.HadGEM3-GC31-LL.ssp585.r1i1p1f1.day.rsus.gr.v20220101"
  },
  "id": "CMIP6.CMIP.NOAA-GFDL.HadGEM3-GC31-LL.ssp585.r1i1p1f1.day.rsus.gr.v20220101",
  "stac_version": "1.0.0",
  "assets": {
    "LUQwruZUyMGJFPFfhpNU": {
      "href": "155",
      "type": "WYsawTecksSJsEKIsvOy",
      "title": "YMaujasuWqSfcuBICEgz",
      "description": null,
      "roles": [
        "AlikiFprMBboVrZWIInE"
      ]
    }
  },
  "links": [
    {
      "href": "http://ceda.stac.ac.uk/collections/cordex/items/CMIP6.CMIP.NOAA-GFDL.HadGEM3-GC31-LL.ssp585.r1i1p1f1.day.rsus.gr.v20220101",
      "rel": "self",
      "type": "application/geo+json"
    },
    {
      "href": "http://ceda.stac.ac.uk/collections/cordex",
      "rel": "parent",
      "type": "application/json"
    },
    {
      "href": "http://ceda.stac.ac.uk/collections/cordex",
      "rel": "collection",
      "type": "application/json"
    },
    {
      "href": "http://ceda.stac.ac.uk",
      "rel": "root",
      "type": "application/json"
    }
  ],
  "stac_extensions": [],
  "collection": "cordex"
}

Done
```

## Further Work

- [*] Simulate a second "Core Node" (approximating Globus)
- [*] Provide an ingest API per simulated ESGF Core Node 
- [ ] Provide Update and Revoke functionality
- [ ] Provide replicate functionality
- [*] Move to ESGF or CEDA repository
- [ ] Publish images to docker hub (ESGF account)
- [ ] Provide Helm charts
- [ ] Fix loging on the ingest API
- [ ] Fully document
- [ ] Improve CLI functionality
- [ ] Move common modules and models to a shared library on pypi
- [ ] Handle POSTs to STAC if the item already exists (should produce an error)
- [ ] MongoDB (or alternative) persistent message dump

## Basic Use

Start the service:

```console
foo@bar:~$ docker compose build
...
foo@bar:~$ docker compose up -d

```

Wait until all services have started, they should wait for each other in the correct order. Now produce 1000 
randomised CMIP6 / Cordex data:

```console
foo@bar:~$ cd esgf-generator
foo@bar:~$ poetry install
foo@bar:~$ poetry run esgf_generator 1000 --publish --node east
...(many STAC records printed)...
```

After about 1 minute, Kafka will have balanced the newly generated topics. The **East** and **West** nodes should show 
1000 STAC records, and the **secondary** node should show ~200 records (only the `historical` experiment).

## Development

It is important to realise that this repo contains three independent Python projects. You should intialise poetry for all three 
of these:

```console
foo@bar:~$ cd esgf-generator
foo@bar:~$ poetry install
foo@bar:~$ cd ../esgf-consumer
foo@bar:~$ poetry install
foo@bar:~$ cd ../esgf-transaction-api
foo@bar:~$ poetry install
```

Poetry will ensure that the correct underlying virtual environment is used for which ever direcrtory you are working in. If 
you are using an IDE, it would be beneficial to set up three different interpreters, for example with PyCharm:

https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html#i5ghoy0_355

You can typically create as many interpreters as you wish.

## Errors

Any errors produced by the consumers are passed back into a special topic in kafka called `esgf_error`. They 
can be viewed at http://localhost:8080/console/default/topics/esgf_error?tab=consume, and contain the original payload 
and the python traceback.

### Kakfa UI

Go to http://localhost:8080 (the UI for KAFKA) and register and account with username `admin@admin.io` and password 
`admin`, then log in with those credentials.

This UI provides a complete view of the stage of your Kafka service and is described here https://www.conduktor.io/console/.

### STAC Browser

A STAC browser simulating the **East** ESGF index is available at http://localhost:9011. This service should be listening 
to all the publication, retraction and update events in the Kafka queue.

A STAC browser simulating the **West** ESGF index is available at http://localhost:9015. This service should be listening 
to all the publication, retraction and update events in the Kafka queue.

A STAC browser simulating a **secondary** ESGF index is also available at http://localhost:9013. This service is 
only listening to certain event in the Kafka queue.

### STAC OpenAPI Browser

A STAC OpenAPI browser simulating the **East** ESGF index is available at http://localhost:9010.

A STAC OpenAPI browser simulating the **West** ESGF index is available at http://localhost:9014.

A STAC OpenAPI browser simulating a **secondary** ESGF index is available at http://localhost:9012.
