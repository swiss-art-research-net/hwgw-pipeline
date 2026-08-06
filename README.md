# Data Extraction Pipeline for the digital »Heinrich Wölfflin - Gesammelte Werke« project
Semantic transformations of the Digital Edition of the »Heinrich Wölfflin - Gesammelte Werke« project 

## How to use

Prerequisites: [Docker](http://docker.io) including Docker Compose

Copy the `.env.example` into `.env` and edit as required (ex. GITHUB_USERNAME and GITHUB_PERSONAL_ACCESS_TOKEN)
```sh
cp .env.example .env
```

Run the project with
```sh
docker compose up -d
```

### Running the pipeline

The pipeline can be controlled by the Task runner. You can run the default task to execute all the commands in order in in the Taskfile

```sh
docker compose exec jobs task
```

## DTS api

The Dapytains api implementation of DTS will be available at http://localhost:8000/collection/.

### DTS Harvester Integration

The hwgw-dts submodule is available in Docker at `/external/hwgw-dts` and can be executed through Task targets.

Submodule install/update:

```sh
git submodule update --init --recursive
git submodule update --remote external/hwgw-dts
```

The harvester task is scoped to the HWGW collection by default (`https://example.org/dts/collections/hwgw`).
At the moment this corresponds to the three SCHRIFTEN collections (`s01`, `s03`, `s04`).

```sh
docker compose exec jobs task dts-harvest-jsonld
docker compose exec jobs task dts-harvest-jsonld OUTPUT=/external/hwgw-dts/data/output/rs4_integration_test.ttl -- --max-resources 1
docker compose exec jobs task dts-harvest-jsonld COLLECTION_ID=https://example.org/dts/collections/hwgw/s01
docker compose exec jobs task dts-harvest-jsonld COLLECTION_ID=https://example.org/dts/collections/hwgw/s03
docker compose exec jobs task dts-harvest-jsonld COLLECTION_ID=https://example.org/dts/collections/hwgw/s04
```

To build the entities-passages index:

```sh
docker compose exec jobs task dts-build-entities-passages-index RESOURCE_ID=https://example.org/dts/collections/hwgw/s03/ed
```


## Tasks

The pipeline can be controlled by the [Task](https://taskfile.dev/#/) runner. The tasks are defined in the `Taskfile.yml` file.

To list available tasks, run:

```sh
docker compose exec jobs task --list
```

This will output a list of tasks:

```
* default:                                     Default task
* download-all-data:                           Download all data from GitHub
* download-mapping-files-from-3M:              Downloads the mapping file from the 3M
* dts-build-entities-passages-index:           Build entities-passages CSV index from DTS TEI documents using external/hwgw-dts.
* dts-harvest-jsonld:                          Harvest JSON-LD from a DTS endpoint using external/hwgw-dts and write a Turtle file.
* ingest-classifications:                      Ingest classifications into the triplestore
* ingest-items:                                Ingest items for all modules. Add --debug true To see the response from the triplestore
* ingest-ontologies:                           Ingests the ontologies into individual named Graphs
* perform-mapping-for-module-items:            Performs the mapping for a specific module. The module name should be passed as an argument or via the MODULE variable.
* prepare-and-perform-mapping-for-items:       Prepares and performs the mapping for all modules
* prepare-dts-catalog-data:                    Prepares the data for the DTS catalog. This includes creating the collection XML and preparing the TEI files.
* prepare-mapping-for-module-items:            Prepares the mapping for a specific module. The module name should be passed as an argument or via the MODULE variable.
* reset:                                       Delete all artefacts produced by the pipeline.
* reset-last-ingested-metadata:                Resets the last ingested metadata for a specific module. Pass the module name as an argument and optionally a new date (YYYY-MM-DD).
* reset-last-mapped-metadata:                  Resets the last mapped metadata for a specific module. Pass the module name as an argument and optionally a new date (YYYY-MM-DD).
* reset-module:                                Delete all artefacts produced by the pipeline for a given module. The module name should be passed as an argument or via the MODULE variable.
```

To run a specific task type `task` followed by the task name, e.g.:

```sh
docker compose exec jobs task ingest-items
```

If the task is already up to date, it will not run. To force a task to run, type the command followed by `--force`

```sh
docker compose exec jobs task ingest-items --force
```

To add additional arguments to the task itself, enter the arguments after a `--` sign, e.g.:

```sh
docker compose exec jobs task reset-last-mapped-metadata -- object
```
