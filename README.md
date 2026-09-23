# Data Extraction Pipeline for the digital »Heinrich Wölfflin - Gesammelte Werke« project
Semantic transformations of the Digital Edition of the »Heinrich Wölfflin - Gesammelte Werke« project 

## How to use

Prerequisites: [Docker](http://docker.io) including Docker Compose, and `git` with the `external/hwgw-dts` submodule checked out.

Copy the `.env.example` into `.env` and edit as required (ex. GITHUB_USERNAME, GITHUB_PERSONAL_ACCESS_TOKEN, QLEVER_ACCESS_TOKEN, and the ports):
```sh
cp .env.example .env
```

The repository root has a `docker-compose.yml` that composes the **base + local** overlays by default, so a plain `docker compose up` publishes the service ports directly on the host.
```sh
docker compose up -d
```

For a production deployment behind a reverse proxy, set `COMPOSE_FILE` to the **base + prod** overlays (and `PROXY_NETWORK_NAME`) instead — see the *Production deployment* section below.

### Running the pipeline

The pipeline can be controlled by the Task runner. You can run the default task to execute all the commands in order in the Taskfile

```sh
docker compose exec jobs task --force
```

Use `--force` on the first run so freshly downloaded/synthesized steps are not skipped. Omit it on later runs (`task` will skip up-to-date steps).

## DTS api

The DapyTains DTS API is available at `http://localhost:${SERVER_PORT}/` (default `8000`, see `.env`; the development `.env` often uses `4000`).

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

`dts-build-combined-rdf` harvests DTS data, indexes passage references, combines them with `mapping/register-entity-index.csv`, and verifies the resulting Turtle.
All generated files are written to `external/hwgw-dts/data/output/`.

By default, all `dts-*` tasks use the local DapyTains DTS endpoint
(`http://dapytains:4000/`) and write `local_hwgw_*` files:

```sh
docker compose exec jobs task dts-build-combined-rdf
```

To explicitly run against the remote RS4 DTS endpoint instead, override both `DTS_ENTRYPOINT` and `DTS_OUTPUT_PREFIX` together, so remote output never mixes with local output:

```sh
docker compose exec jobs task dts-build-combined-rdf \
	DTS_ENTRYPOINT=http://rs4.ethz.ch/dts/ \
	DTS_OUTPUT_PREFIX=hwgw
```

Both local and remote runs use the API-compliant `uri-template` mode by default.

The local viewer workaround is separate and disabled by default. To enable it, set `DAPYTAINS_VIEWER_WORKAROUND=true` in `.env` and rebuild DapyTains:

```sh
docker compose build dapytains
docker compose up -d dapytains
```

When running the enriched RDF task against that viewer-enabled service, pass `VIEWER_WORKAROUND=true`; this is the only case where the task passes `--endpoint-style concrete` to the DTS scripts.

To add RDS `owl:sameAs` links for HWGW entities with GND identifiers, run:

```sh
docker compose exec jobs task dts-build-full-rdf
```

This first builds the combined RDF (`dts-build-combined-rdf`), then adds RDS links (`dts-add-rds-links`), which queries the RDS `extend` endpoint in batches using `https://d-nb.info/gnd/<id>` identifiers derived from the register. 

RDS links are written to a separate file from the combined DTS graph: `external/hwgw-dts/data/output/local_hwgw_rds_links.ttl`, containing only `owl:sameAs` triples, alongside the unmodified `local_hwgw_combined.ttl`.

The RDS endpoint is configurable via `RDS_ENDPOINT` in `.env` (default `https://reconcile.rds.swissartresearch.net/`) and must be reachable from the `jobs` container.

## Inspecting the RDF output with QLever

A [QLever](https://github.com/ad-freiburg/qlever) SPARQL endpoint is available to browse and query the pipeline's RDF output.

Start it:

```sh
docker compose up -d qlever
```

Build (or rebuild) the index from the current pipeline output and start the QLever server. This must be run on the **host**, not via `docker compose exec jobs task`, since it needs to run `docker compose exec` against the `qlever` service itself:

```sh
./scripts/reindex-qlever.sh
```

Then query the SPARQL endpoint at `http://localhost:${PORT_QLEVER}` (default `7011`, see `.env`), e.g.:

```sh
curl -s -X POST -H 'Content-Type: application/sparql-query' \
  -H 'Accept: application/sparql-results+json' \
  --data-binary 'SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }' \
  http://localhost:7011
```


### QLever UI (browser interface)

Start [QLever UI](https://github.com/ad-freiburg/qlever-ui):

```sh
docker compose up -d qlever-ui
```

Its database and `admin` account are created automatically on first start - no manual setup step needed. The superuser credentials come from `.env` (`QLEVER_UI_USERNAME`/`QLEVER_UI_PASSWORD`, default `admin`/`changeme`), to be  changed before deploying in production. Then, once (via the browser):
1. Open `http://localhost:${PORT_QLEVER_UI}` (default `7012`) `/admin` and log in with
   `QLEVER_UI_USERNAME`/`QLEVER_UI_PASSWORD`.
2. Under "Backends", add a backend with SPARQL endpoint `http://localhost:${PORT_QLEVER}`
   (default `http://localhost:7011`).
3. Open `http://localhost:${PORT_QLEVER_UI}`, select the new backend, and start querying.


## Production deployment

The compose stack is split into a shared base file plus environment overlays, selected
via `COMPOSE_FILE` in `.env`:

- `docker-compose.base.yml` — shared service definitions (no host ports published).
- `docker-compose.local.yml` — direct host port mappings, for local development.
- `docker-compose.prod.yml` — reverse-proxy overlay for a deployed server.

Local/development (default):
```sh
COMPOSE_FILE=./docker-compose.base.yml:./docker-compose.local.yml
docker compose up -d
```

Production (behind a reverse proxy):
```sh
COMPOSE_FILE=./docker-compose.base.yml:./docker-compose.prod.yml
PROXY_NETWORK_NAME=<name-of-your-proxy-network>
docker compose up -d
```


Production checklist:
1. **Secrets** — set `GITHUB_PERSONAL_ACCESS_TOKEN`, `QLEVER_ACCESS_TOKEN`, and `QLEVER_UI_USERNAME`/`QLEVER_UI_PASSWORD`.
2. **Build on the server** (`docker compose build --no-cache`) — the base image is Debian Bookworm
3. Check out the `external/hwgw-dts` submodule (`git submodule update --init --recursive`).
4. Run the pipeline (`docker compose exec jobs task --force`). If `DTS` catalog/volumes changed (e.g. a new `SCHRIFTEN`), restart `dapytains` after `prepare-dts-catalog-data` so it serves the new catalog, then build the QLever index: `./scripts/reindex-qlever.sh`.
5. Configure the reverse proxy to forward to `dapytains:${SERVER_PORT}`, `qlever:7001` and `qlever-ui:7000` on the proxy network.


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

## Tasks

The pipeline can be controlled by the [Task](https://taskfile.dev/#/) runner. The tasks are defined in the `scripts/Taskfile.yml` file.


To list available tasks, run:

```sh
docker compose exec jobs task --list
```

This will output a list of tasks:

```
* default:                                     Default task
* download-all-data:                           Download all data from GitHub
* dts-add-rds-links:                           Build a standalone owl:sameAs Turtle graph (_rds_links.ttl) from RDS matches, kept separate from the DTS combined graph.
* dts-build-combined-rdf:                      Harvest, index, combine and verify HWGW RDF from a DTS endpoint (no RDS enrichment); writes only to external/hwgw-dts/data/output.
* dts-build-entities-passages-index:           Build one entities-passages CSV index from all resources declared in the selected HWGW volume catalogs.
* dts-build-full-rdf:                          Full pipeline - build combined HWGW RDF (dts-build-combined-rdf) and a separate RDS owl:sameAs graph (dts-add-rds-links).
* dts-harvest-jsonld:                          Harvest JSON-LD from a DTS endpoint using external/hwgw-dts and write a Turtle file.
* generate-entity-index:                       Generate CSV index of mapped person/object/org/place entities and URIs
* perform-mapping-for-module-items:            Performs the mapping for a specific module. The module name should be passed as an argument or via the MODULE variable.
* prepare-and-perform-mapping-for-items:       Prepares and performs the mapping for all modules
* prepare-dts-catalog-data:                    Prepares the data for the DTS catalog. This includes creating the collection XML and preparing the TEI files.
* prepare-mapping-for-module-items:            Prepares the mapping for a specific module. The module name should be passed as an argument or via the MODULE variable.
* reset:                                       Delete all artefacts produced by the pipeline.
* reset-module:                                Delete all artefacts produced by the pipeline for a given module. The module name should be passed as an argument or via the MODULE variable.
```

To run a specific task type `task` followed by the task name, e.g.:

```sh
docker compose exec jobs task prepare-mapping-for-module-items -- objects
docker compose exec jobs task dts-build-combined-rdf
```

If the task is already up to date, it will not run. To force a task to run, type the command followed by `--force`:

```sh
docker compose exec jobs task dts-build-combined-rdf --force
```

To add additional arguments to the task itself, enter the arguments after a `--` sign, e.g.:

```sh
docker compose exec jobs task reset-last-mapped-metadata -- objects
```

## Credits
This pipeline has been developed by SARI/UZH in the context of a project funded by Digital Visual Studies/UZH and the The Bibliotheca Hertziana – Max Planck Institute for Art History.  
