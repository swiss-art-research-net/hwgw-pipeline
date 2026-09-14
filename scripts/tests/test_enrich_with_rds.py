import csv
import sys
from pathlib import Path

from rdflib import Graph, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrich_with_rds import EnrichmentStats, enrich_graph, load_gnd_entities, OWL  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def get(self, endpoint, params, timeout):
        return FakeResponse(
            {
                "rows": {
                    "https://d-nb.info/gnd/118582143": {
                        "matches": [{"str": "http://www.wikidata.org/entity/Q5592"}]
                    }
                }
            }
        )


def test_load_gnd_entities_derives_rds_uri(tmp_path):
    path = tmp_path / "register.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["type", "crm", "local_id", "uri"])
        writer.writeheader()
        writer.writerow(
            {
                "type": "person",
                "crm": "E21_Person",
                "local_id": "gnd-118582143",
                "uri": "https://hwgw.uzh.ch/person/gnd-118582143",
            }
        )
        writer.writerow(
            {
                "type": "object",
                "crm": "E22_Human-Made_Object",
                "local_id": "object-example",
                "uri": "https://hwgw.uzh.ch/artwork/object-example",
            }
        )

    entities, stats = load_gnd_entities(path)

    assert entities == {
        "https://d-nb.info/gnd/118582143": "https://hwgw.uzh.ch/person/gnd-118582143"
    }
    assert stats.gnd_entities == 1
    assert stats.skipped_entities == 1


def test_enrich_graph_adds_owl_same_as_links():
    graph = Graph()
    stats = EnrichmentStats()
    entities = {
        "https://d-nb.info/gnd/118582143": "https://hwgw.uzh.ch/person/gnd-118582143"
    }

    import enrich_with_rds

    original_session = enrich_with_rds.requests.Session
    enrich_with_rds.requests.Session = lambda: FakeSession()
    try:
        enrich_graph(graph, entities, "http://rds.example/", 100, 1, 0, 0, stats)
    finally:
        enrich_with_rds.requests.Session = original_session

    assert (
        URIRef("https://hwgw.uzh.ch/person/gnd-118582143"),
        OWL.sameAs,
        URIRef("http://www.wikidata.org/entity/Q5592"),
    ) in graph
    assert stats.links_added == 1
