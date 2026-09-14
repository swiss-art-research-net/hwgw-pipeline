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

## Inspecting the RDF output with QLever

A [QLever](https://github.com/ad-freiburg/qlever) SPARQL endpoint is available to browse and
query the pipeline's RDF output (`local_hwgw_combined.ttl` + `local_hwgw_rds_links.ttl`).

Start it:

```sh
docker compose up -d qlever
```

Build (or rebuild) the index from the current pipeline output and start the QLever server.
This must be run on the **host**, not via `docker compose exec jobs task`, since it needs to
run `docker compose exec` against the `qlever` service itself:

```sh
./scripts/reindex-qlever.sh
```

Then query the SPARQL endpoint at `http://localhost:${PORT_QLEVER}` (default `7011`, see
`.env`), e.g.:

```sh
curl -s -X POST -H 'Content-Type: application/sparql-query' \
  -H 'Accept: application/sparql-results+json' \
  --data-binary 'SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }' \
  http://localhost:7011
```


### QLever UI (browser interface)

Start
[QLever UI](https://github.com/ad-freiburg/qlever-ui):

```sh
docker compose up -d qlever-ui
```

Its database and `admin`/`admin` account are created automatically on first start - no manual setup step needed. Then, once (via the browser):
1. Open `http://localhost:${PORT_QLEVER_UI}` (default `7012`) `/admin` and log in as `admin`/`admin`.
2. Under "Backends", add a backend with SPARQL endpoint `http://localhost:${PORT_QLEVER}`
   (default `http://localhost:7011`).
3. Open `http://localhost:${PORT_QLEVER_UI}`, select the new backend, and start querying.

## DTS api

The DapyTains DTS API is available at `http://localhost:4000/`.

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

### Build combined RDF

`dts-build-combined-rdf` harvests DTS data, indexes passage references, combines
them with `mapping/register-entity-index.csv`, and verifies the resulting Turtle.
All generated files are written to `external/hwgw-dts/data/output/`.

By default, all `dts-*` tasks use the local DapyTains DTS endpoint
(`http://dapytains:4000/`) and write `local_hwgw_*` files:

```sh
docker compose exec jobs task dts-build-combined-rdf
```

To explicitly run against the remote RS4 DTS endpoint instead, override both
`DTS_ENTRYPOINT` and `DTS_OUTPUT_PREFIX` together, so remote output never mixes with local output:

```sh
docker compose exec jobs task dts-build-combined-rdf \
	DTS_ENTRYPOINT=http://rs4.ethz.ch/dts/ \
	DTS_OUTPUT_PREFIX=hwgw
```

Both local and remote runs use the API-compliant `uri-template` mode by default.

The local viewer workaround is separate and disabled by default. To enable it,
set `DAPYTAINS_VIEWER_WORKAROUND=true` in `.env` and rebuild DapyTains:

```sh
docker compose build dapytains
docker compose up -d dapytains
```

When running the enriched RDF task against that viewer-enabled service, pass
`VIEWER_WORKAROUND=true`; this is the only case where the task passes
`--endpoint-style concrete` to the DTS scripts.

To add RDS `owl:sameAs` links for HWGW entities with GND identifiers, run:

```sh
docker compose exec jobs task dts-build-full-rdf
```

This first builds the combined RDF (`dts-build-combined-rdf`), then adds RDS
links (`dts-add-rds-links`), which queries the RDS `extend` endpoint in
batches using `https://d-nb.info/gnd/<id>` identifiers derived from the register.
RDS links are written to a separate file from the combined DTS graph: `external/hwgw-dts/data/output/local_hwgw_rds_links.ttl`, containing
only `owl:sameAs` triples, alongside the unmodified `local_hwgw_combined.ttl`.
Override `RDS_ENDPOINT` when RDS is exposed at another host or port.


## Tasks

The pipeline can be controlled by the [Task](https://taskfile.dev/#/) runner. The tasks are defined in the `scripts/Taskfile.yml` file.

## Mappings

Mapping definitions are in:
- `mapping/mapping-objects.x3ml`
- `mapping/mapping-organizations.x3ml`
- `mapping/mapping-persons.x3ml`
- `mapping/mapping-places.x3ml`

Prepared mapping input is written to `mapping/input/<module>/` and mapping output TTL is written to `mapping/output/<module>/`.

Supported mapping modules:
- `objects`
- `organizations`
- `persons`
- `places`

Run mapping for one module:

```sh
docker compose exec jobs task prepare-mapping-for-module-items -- objects
docker compose exec jobs task perform-mapping-for-module-items -- objects
```

Run mapping for all modules:

```sh
docker compose exec jobs task prepare-and-perform-mapping-for-items
```

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
docker compose exec jobs task reset-last-mapped-metadata -- objects
```
