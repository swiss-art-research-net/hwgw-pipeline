#!/usr/bin/env python3
"""
Build a standalone owl:sameAs Turtle graph from RDS matches for HWGW GND entities.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from rdflib import Graph, Namespace, URIRef
from tqdm.auto import tqdm

LOGGER = logging.getLogger("hwgw_rds_enrichment")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
RDS_DEFAULT_ENDPOINT = "http://localhost:8000/"

# Namespace prefixes of the datasets RDS reconciles against
# Matches outside these namespaces are not real RDS datasets and are dropped
RDS_DATASET_NAMESPACES = (
    "http://vocab.getty.edu/aat/",
    "https://sws.geonames.org/",
    "https://d-nb.info/gnd/",
    "https://resource.gta.arch.ethz.ch/",
    "http://id.loc.gov/authorities/names/",
    "https://recherche.sik-isea.ch/person-",
    "http://data.culture.fr/thesaurus/resource/ark:/67717/T96/",
    "http://data.culture.fr/thesaurus/resource/ark:/67717/T69/",
    "http://vocab.getty.edu/ulan/",
    "http://www.wikidata.org/entity/",
)


def is_rds_dataset_uri(uri: str) -> bool:
    return uri.startswith(RDS_DATASET_NAMESPACES)


@dataclass
class EnrichmentStats:
    register_rows: int = 0
    gnd_entities: int = 0
    skipped_entities: int = 0
    batches: int = 0
    request_failures: int = 0
    matches: int = 0
    non_dataset_matches_skipped: int = 0
    links_added: int = 0


def configure_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        filename=log_file,
        filemode="w",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-index", required=True, help="HWGW register index CSV.")
    parser.add_argument("--output", required=True, help="Output Turtle graph containing only owl:sameAs RDS links.")
    parser.add_argument("--endpoint", default=RDS_DEFAULT_ENDPOINT, help="RDS reconciliation endpoint.")
    parser.add_argument("--batch-size", type=int, default=100, help="GND IDs per RDS request.")
    parser.add_argument("--timeout", type=float, default=60, help="Request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Retries for transient RDS failures.")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Initial retry delay in seconds.")
    parser.add_argument("--log-file", default="data/logs/enrich_with_rds.log")
    return parser


def load_gnd_entities(path: Path) -> tuple[dict[str, str], EnrichmentStats]:
    stats = EnrichmentStats()
    entities: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"local_id", "uri"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"External index is missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            stats.register_rows += 1
            local_id = (row.get("local_id") or "").strip()
            entity_uri = (row.get("uri") or "").strip()
            if not local_id.startswith("gnd-") or not entity_uri:
                stats.skipped_entities += 1
                continue
            gnd_id = local_id.removeprefix("gnd-")
            entities[f"https://d-nb.info/gnd/{gnd_id}"] = entity_uri
    stats.gnd_entities = len(entities)
    return entities, stats


def _request_payload(ids: list[str]) -> dict[str, Any]:
    return {"ids": ids, "properties": [{"id": "matches"}]}


def fetch_batch(
    session: requests.Session,
    endpoint: str,
    ids: list[str],
    timeout: float,
    retries: int,
    retry_delay: float,
    stats: EnrichmentStats,
) -> dict[str, list[str]]:
    params = {"extend": json.dumps(_request_payload(ids), separators=(",", ":"))}
    for attempt in range(retries + 1):
        try:
            response = session.get(endpoint, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("rows", {})
            if not isinstance(rows, dict):
                raise ValueError("RDS response has no object-valued 'rows' field")
            result: dict[str, list[str]] = {}
            for entity_id, row in rows.items():
                values = row.get("matches", []) if isinstance(row, dict) else []
                result[entity_id] = [
                    str(value.get("str") or value.get("id"))
                    for value in values
                    if isinstance(value, dict) and (value.get("str") or value.get("id"))
                ]
            return result
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            if attempt >= retries:
                stats.request_failures += 1
                LOGGER.error("RDS request failed for batch of %s IDs: %s", len(ids), exc)
                return {}
            delay = retry_delay * (2**attempt)
            LOGGER.warning("RDS request failed (%s); retrying in %.1fs", exc, delay)
            time.sleep(delay)
    return {}


def enrich_graph(
    graph: Graph,
    entities: dict[str, str],
    endpoint: str,
    batch_size: int,
    timeout: float,
    retries: int,
    retry_delay: float,
    stats: EnrichmentStats,
) -> None:
    if batch_size < 1:
        raise ValueError("batch-size must be positive")
    session = requests.Session()
    entity_items = list(entities.items())
    for start in tqdm(range(0, len(entity_items), batch_size), desc="Fetching RDS matches", unit="batch"):
        batch = entity_items[start : start + batch_size]
        stats.batches += 1
        matches_by_id = fetch_batch(
            session, endpoint, [item[0] for item in batch], timeout, retries, retry_delay, stats
        )
        for lookup_id, match_uris in matches_by_id.items():
            subject_uri = entities.get(lookup_id)
            if subject_uri is None:
                LOGGER.warning("RDS returned an unexpected identifier: %s", lookup_id)
                continue
            for match_uri in match_uris:
                if not is_rds_dataset_uri(match_uri):
                    stats.non_dataset_matches_skipped += 1
                    continue
                try:
                    graph.add((URIRef(subject_uri), OWL.sameAs, URIRef(match_uri)))
                except ValueError:
                    LOGGER.warning("Skipping invalid RDS match URI: %r", match_uri)
                    continue
                stats.matches += 1
    stats.links_added = stats.matches


def main() -> int:
    args = build_parser().parse_args()
    configure_logging(args.log_file)
    graph = Graph()
    entities, stats = load_gnd_entities(Path(args.external_index))
    enrich_graph(
        graph,
        entities,
        args.endpoint,
        args.batch_size,
        args.timeout,
        args.retries,
        args.retry_delay,
        stats,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output, format="turtle")
    LOGGER.info("RDS enrichment stats: %s", stats)
    print(
        f"Wrote {len(graph)} owl:sameAs triples to {output}; "
        f"queried {stats.gnd_entities} GND entities and added {stats.links_added} links "
        f"({stats.non_dataset_matches_skipped} non-RDS-dataset matches skipped)."
    )
    return 1 if stats.request_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
