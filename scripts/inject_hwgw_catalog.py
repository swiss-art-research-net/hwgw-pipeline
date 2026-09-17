#!/usr/bin/env python3
"""
Register the HWGW edition as a member of the root DTS catalog.

Usage:
  python inject_hwgw_catalog.py [ROOT_CATALOG.xml]

- Adds  <collection identifier="https://example.org/dts/collections/hwgw"
        filepath="hwgw-edition/collection.xml"/>
  under <collection><members> in the root catalog.
- If <members> is missing, it is created as the last child of <collection>.
"""
import sys
from pathlib import Path
from lxml import etree

HWGW_COLLECTION_ID = "https://example.org/dts/collections/hwgw"
HWGW_FILEPATH = "hwgw-edition/collection.xml"
ROOT_IDENTIFIER = "https://example.org/dts/collections"


def main() -> None:
    catalog_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("/dts_data/catalog/catalog.xml")
    )

    # --- load or create the shared root catalog ---
    if catalog_path.exists():
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(str(catalog_path), parser)
        root = tree.getroot()
        if root is None or root.tag != "collection":
            print(
                f"ERROR: {catalog_path} root element is not <collection>",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        root = etree.Element("collection", identifier=ROOT_IDENTIFIER)
        etree.SubElement(root, "title").text = "DTS Root"
        tree = etree.ElementTree(root)

    # --- find-or-create <members> ---
    members = root.find("members")
    if members is None:
        members = etree.SubElement(root, "members")

    # --- idempotency: skip if already registered by identifier ---
    for c in members.findall("collection"):
        if c.get("identifier") == HWGW_COLLECTION_ID:
            print(f"OK: already registered -> {HWGW_COLLECTION_ID} ({catalog_path})")
            member_file = catalog_path.parent / HWGW_FILEPATH
            state = "exists" if member_file.exists() else "MISSING"
            print(f"   member file: {member_file} ({state})")
            return

    # --- append hwgw as a member (filepath relative to the root catalog) ---
    etree.SubElement(
        members,
        "collection",
        identifier=HWGW_COLLECTION_ID,
        filepath=HWGW_FILEPATH,
    )

    etree.indent(tree, space="  ")
    tree.write(str(catalog_path), xml_declaration=True, encoding="UTF-8")

    member_file = catalog_path.parent / HWGW_FILEPATH
    state = "exists" if member_file.exists() else "MISSING"
    print(f"OK: registered -> {HWGW_COLLECTION_ID} -> {HWGW_FILEPATH}")
    print(f"   catalog:     {catalog_path}")
    print(f"   member file: {member_file} ({state})")


if __name__ == "__main__":
    main()
