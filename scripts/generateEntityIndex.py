#!/usr/bin/env python3
"""
Generate a CSV index of mapped register entities and their URIs.

The script reads:
  - register XML files (persons, organizations, places, objects)
  - mapping X3ML files
  - generator policy XML

It then derives URI rules from the mapping/generator policy and emits a stable CSV:
  type,crm,local_id,uri
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

XML_NS = "http://www.w3.org/XML/1998/namespace"


@dataclass(frozen=True)
class DomainRule:
    source_tag: str
    crm_type: str
    uri_type: str
    allowed_object_types: Optional[Set[str]] = None


@dataclass(frozen=True)
class RegisterConfig:
    logical_type: str
    register_xml: Path
    mapping_x3ml: Path


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_uri_pattern(generator_policy_path: Path) -> Tuple[str, str]:
    tree = ET.parse(generator_policy_path)
    root = tree.getroot()

    for generator in root.findall("./generator"):
        if generator.attrib.get("name") != "URIwithTypeAndId":
            continue
        prefix = generator.attrib.get("prefix")
        pattern_node = generator.find("./pattern")
        if not prefix or pattern_node is None or not (pattern_node.text or "").strip():
            raise ValueError(
                "Generator URIwithTypeAndId must have both prefix and pattern in generator policy."
            )
        return prefix, (pattern_node.text or "").strip()

    raise ValueError("Generator URIwithTypeAndId not found in generator policy.")


def parse_mapping_namespaces(mapping_root: ET.Element) -> Dict[str, str]:
    ns: Dict[str, str] = {}
    for namespace in mapping_root.findall("./namespaces/namespace"):
        prefix = namespace.attrib.get("prefix")
        uri = namespace.attrib.get("uri")
        if prefix and uri:
            ns[prefix] = uri
    return ns


def extract_object_type_filter(source_node_text: str) -> Optional[Set[str]]:
    values = set(re.findall(r"@type='([^']+)'", source_node_text))
    return values or None


def extract_source_tag(source_node_text: str) -> str:
    # Extract all tag-like tokens and use the last one, e.g. //listObject//object[...] -> object
    tags = re.findall(r"(?:^|/)(?:[a-zA-Z_][\w.-]*:)?([a-zA-Z_][\w.-]*)", source_node_text)
    tags = [t for t in tags if t not in {"text", "node"}]
    if not tags:
        raise ValueError(f"Could not determine source tag from source_node: {source_node_text!r}")
    return tags[-1]


def parse_domain_rules(mapping_path: Path) -> List[DomainRule]:
    tree = ET.parse(mapping_path)
    root = tree.getroot()
    rules: List[DomainRule] = []

    for mapping in root.findall("./mappings/mapping"):
        domain = mapping.find("./domain")
        if domain is None:
            continue

        source_node = domain.find("./source_node")
        target_entity = domain.find("./target_node/entity")
        if source_node is None or target_entity is None:
            continue

        instance_generator = target_entity.find("./instance_generator")
        if instance_generator is None or instance_generator.attrib.get("name") != "URIwithTypeAndId":
            continue

        crm_type_text = (target_entity.findtext("./type") or "").strip()
        if not crm_type_text:
            continue

        uri_type_value = None
        for arg in instance_generator.findall("./arg"):
            if arg.attrib.get("name") == "type" and arg.attrib.get("type") == "constant":
                uri_type_value = (arg.text or "").strip()
                break

        if not uri_type_value:
            continue

        source_node_text = (source_node.text or "").strip()
        if not source_node_text:
            continue

        source_tag = extract_source_tag(source_node_text)
        object_type_filter = extract_object_type_filter(source_node_text) if source_tag == "object" else None

        rules.append(
            DomainRule(
                source_tag=source_tag,
                crm_type=crm_type_text.replace("crm:", ""),
                uri_type=uri_type_value,
                allowed_object_types=object_type_filter,
            )
        )

    if not rules:
        raise ValueError(f"No domain rules using URIwithTypeAndId found in {mapping_path}")
    return rules


def find_xml_id(element: ET.Element) -> Optional[str]:
    value = element.attrib.get(f"{{{XML_NS}}}id")
    if value:
        return value.strip()
    value = element.attrib.get("xml:id")
    if value:
        return value.strip()
    return None


def matches_rule(element: ET.Element, rule: DomainRule) -> bool:
    if local_name(element.tag) != rule.source_tag:
        return False
    if rule.allowed_object_types is None:
        return True
    object_type = (element.attrib.get("type") or "").strip()
    return object_type in rule.allowed_object_types


def build_uri(base: str, pattern: str, *, uri_type: str, local_id: str) -> str:
    return (base + pattern.replace("{type}", uri_type).replace("{id}", local_id)).rstrip("/")


def collect_rows_for_register(
    config: RegisterConfig,
    *,
    prefix_uri_map: Dict[str, str],
    uri_prefix_name: str,
    uri_pattern: str,
) -> List[Tuple[str, str, str, str]]:
    rules = parse_domain_rules(config.mapping_x3ml)

    if uri_prefix_name not in prefix_uri_map:
        raise ValueError(
            f"Prefix '{uri_prefix_name}' from generator policy was not found in mapping namespaces "
            f"({config.mapping_x3ml})."
        )
    base_uri = prefix_uri_map[uri_prefix_name]

    root = ET.parse(config.register_xml).getroot()
    rows: List[Tuple[str, str, str, str]] = []
    unresolved = 0

    for element in root.iter():
        tag_name = local_name(element.tag)
        candidate_rules = [rule for rule in rules if rule.source_tag == tag_name]
        if not candidate_rules:
            continue

        matched_rule = next((rule for rule in candidate_rules if matches_rule(element, rule)), None)
        if matched_rule is None:
            if tag_name == "object":
                unresolved += 1
            continue

        local_id = find_xml_id(element)
        if not local_id:
            continue

        uri = build_uri(base_uri, uri_pattern, uri_type=matched_rule.uri_type, local_id=local_id)
        rows.append((config.logical_type, matched_rule.crm_type, local_id, uri))

    if unresolved:
        print(
            f"[WARN] {config.register_xml.name}: {unresolved} object elements did not match an object mapping domain.",
            file=sys.stderr,
        )

    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate full CSV index of mapped register entities and URIs."
    )
    parser.add_argument("--persons-xml", required=True, type=Path, help="Path to persons register XML")
    parser.add_argument(
        "--organizations-xml", required=True, type=Path, help="Path to organizations register XML"
    )
    parser.add_argument("--places-xml", required=True, type=Path, help="Path to places register XML")
    parser.add_argument("--objects-xml", required=True, type=Path, help="Path to objects register XML")

    parser.add_argument(
        "--persons-mapping", required=True, type=Path, help="Path to mapping-persons.x3ml"
    )
    parser.add_argument(
        "--organizations-mapping",
        required=True,
        type=Path,
        help="Path to mapping-organizations.x3ml",
    )
    parser.add_argument("--places-mapping", required=True, type=Path, help="Path to mapping-places.x3ml")
    parser.add_argument("--objects-mapping", required=True, type=Path, help="Path to mapping-objects.x3ml")
    parser.add_argument("--generator-policy", required=True, type=Path, help="Path to generator-policy.xml")
    parser.add_argument("--output", required=True, type=Path, help="Output CSV path")

    return parser.parse_args()


def ensure_paths_exist(paths: Sequence[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files:\n  - " + "\n  - ".join(missing))


def main() -> int:
    args = parse_args()

    ensure_paths_exist(
        [
            args.persons_xml,
            args.organizations_xml,
            args.places_xml,
            args.objects_xml,
            args.persons_mapping,
            args.organizations_mapping,
            args.places_mapping,
            args.objects_mapping,
            args.generator_policy,
        ]
    )

    uri_prefix_name, uri_pattern = parse_uri_pattern(args.generator_policy)

    mapping_for_namespaces = args.persons_mapping
    mapping_ns = parse_mapping_namespaces(ET.parse(mapping_for_namespaces).getroot())
    if uri_prefix_name not in mapping_ns:
        raise ValueError(
            f"Prefix '{uri_prefix_name}' from generator policy not found in mapping namespaces "
            f"({mapping_for_namespaces})."
        )

    configs = [
        RegisterConfig("person", args.persons_xml, args.persons_mapping),
        RegisterConfig("organization", args.organizations_xml, args.organizations_mapping),
        RegisterConfig("place", args.places_xml, args.places_mapping),
        RegisterConfig("object", args.objects_xml, args.objects_mapping),
    ]

    all_rows: List[Tuple[str, str, str, str]] = []
    for config in configs:
        mapping_ns_for_config = parse_mapping_namespaces(ET.parse(config.mapping_x3ml).getroot())
        rows = collect_rows_for_register(
            config,
            prefix_uri_map=mapping_ns_for_config,
            uri_prefix_name=uri_prefix_name,
            uri_pattern=uri_pattern,
        )
        all_rows.extend(rows)

    # Deduplicate and guard against conflicting URI assignments.
    by_key: Dict[Tuple[str, str], str] = {}
    for entity_type, _crm, local_id, uri in all_rows:
        key = (entity_type, local_id)
        previous = by_key.get(key)
        if previous is not None and previous != uri:
            raise ValueError(
                f"Conflicting URI assignments for {entity_type}:{local_id} -> {previous} vs {uri}"
            )
        by_key[key] = uri

    unique_rows = sorted(set(all_rows), key=lambda row: (row[0], row[2], row[3]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "crm", "local_id", "uri"])
        writer.writerows(unique_rows)

    print(f"Wrote {len(unique_rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
