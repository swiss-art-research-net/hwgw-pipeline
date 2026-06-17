#!/usr/bin/env python3

import argparse
from pathlib import Path
from lxml import etree

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def parse_xml(path):
    parser = etree.XMLParser(remove_blank_text=True)
    return etree.parse(str(path), parser)


def write_xml_with_schema(tree, output_path):
    
    root = tree.getroot()

    pi = etree.ProcessingInstruction(
        "oxygen",
        'RNGSchema="schema.rng" type="xml"'
    )

    root.addprevious(pi)

    tree.write(
        output_path,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8"
    )


def extract_root_series_title(tei_file):
    tree = parse_xml(tei_file)
    el = tree.xpath(
        "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt/tei:title[1]",
        namespaces=NS
    )
    return el[0].text.strip() if el else "Untitled Collection"


def extract_volume_titles(tei_file):
    tree = parse_xml(tei_file)

    volume = tree.xpath(
        "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='volume']",
        namespaces=NS
    )

    monograph = tree.xpath(
        "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@level='m']",
        namespaces=NS
    )

    titles = []

    if volume:
        titles.append(volume[0].text.strip())

    if monograph:
        titles.append(monograph[0].text.strip())

    return titles

def extract_authors(tei_file):
    tree = parse_xml(tei_file)
    # authors = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author", namespaces=NS)
    authors = tree.xpath('/tei:TEI/tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:bibl[@type="printed_edition"]/tei:author', namespaces=NS)
    return [a.text.strip() for a in authors if a.text]

def extract_editors(tei_file):
    tree = parse_xml(tei_file)
    # editors = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:editor", namespaces=NS)
    editors = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:bibl/tei:editor/tei:name", namespaces=NS)
    return [e.text.strip() for e in editors if e.text]

def extract_publishers(tei_file):
    tree = parse_xml(tei_file)
    publishers = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:publisher", namespaces=NS)
    return [p.text.strip() for p in publishers if p.text]

def extract_dates(tei_file):
    tree = parse_xml(tei_file)
    dates = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:date", namespaces=NS)
    result = []
    for d in dates:
        if d.text:
            result.append(d.text.strip())
        elif "when" in d.attrib:
            result.append(d.attrib["when"])
    return result

def extract_languages(tei_file):
    tree = parse_xml(tei_file)
    langs = tree.xpath("/tei:TEI/tei:teiHeader/tei:profileDesc/tei:langUsage/tei:language", namespaces=NS)
    result = []
    for l in langs:
        if l.text:
            result.append(l.text.strip())
        elif "ident" in l.attrib:
            result.append(l.attrib["ident"])
    return result

def extract_license(tei_file):
    tree = parse_xml(tei_file)
    availability = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:availability", namespaces=NS)
    if availability and availability[0].text:
        return [availability[0].text.strip()]
    # If availability has p child, get its text
    p = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:availability/p", namespaces=NS)
    if p and p[0].text:
        return [p[0].text.strip()]
    return []

def extract_series(tei_file):
    tree = parse_xml(tei_file)
    # Get all <title> under <seriesStmt>
    series_titles = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt/tei:title", namespaces=NS)
    return [s.text.strip() for s in series_titles if s.text]


def build_webview_url(xml_id: str, tei_filename: str) -> str:
    """
    Build viewer URL.
    """

    volume = tei_filename.split("-")[0]

    return (
        f"https://hwgw.humanitiesconnect.pub/{volume}/"
        f"{tei_filename}"
        f"?view=div&pers=0&org=0&place=0&obj=0&bibl=0&pb=0"
        f"#{xml_id}"
    )
    
def inject_webview_urls(tree, tei_filename):
    """
    Add data-webview attribute to every element carrying xml:id.
    """

    xml_ns = "{http://www.w3.org/XML/1998/namespace}"

    for elem in tree.xpath(
        """
          //tei:div[@xml:id]
        | //tei:div/tei:p[@xml:id]
        | //tei:pb[@xml:id]
        """, 
        namespaces=NS):
        xml_id = elem.get(f"{xml_ns}id")

        if xml_id:
            elem.set("data-webview", build_webview_url(xml_id, tei_filename))

    return tree


# --- Dynamic refsDecl/citeStructure generation ---
def analyze_body_structure_and_build_citestructure(tree):
    """
    Analyze the TEI body structure and build a refsDecl/citeStructure tree.
    Handles arbitrary div nesting and direct paragraphs at any level.
    """
    body = tree.find('.//tei:body', namespaces=NS)
    if body is None:
        return None

    def deepest_div_path(parent, is_top_level=False):
        # Prefer div[@type='chapter'] if present
        divs = [el for el in parent if el.tag.endswith('div')]
        chapter_div = None
        for d in divs:
            if d.attrib.get('type') == 'chapter':
                chapter_div = d
                break
        if chapter_div is not None:
            typ = 'chapter'
            if is_top_level:
                match = f"//body/div[@type='chapter']"
                cs = etree.Element('citeStructure', unit=typ, match=match, use='@xml:id')
            else:
                match = f"div[@type='chapter']"
                cs = etree.Element('citeStructure', unit=typ, match=match, use='@xml:id', delim=":")
            # Inject <citeData property="http://purl.org/dc/terms/title" use="head/@n"/> for chapters
            cite_data = etree.Element('citeData', property="http://purl.org/dc/terms/title", use="head/@n")
            cs.append(cite_data)
            
            webview_data = etree.Element('citeData', property="https://schema.org/url", use="@data-webview")
            cs.append(webview_data)
            
            child = deepest_div_path(chapter_div, is_top_level=False)
            if child is not None:
                cs.append(child)
            return cs
        # Otherwise, pick the first div (subchapter or other div)
        if divs:
            d = divs[0]
            typ = d.attrib.get('type', 'div')
            if is_top_level:
                match = f"//body/div[@type='{typ}']"
                cs = etree.Element('citeStructure', unit=typ, match=match, use='@xml:id')
            else:
                match = f"div[@type='{typ}']"
                cs = etree.Element('citeStructure', unit=typ, match=match, use='@xml:id', delim=":")
            # Inject <citeData property="http://purl.org/dc/terms/title" use="head/@n"/> for all divs
            cite_data = etree.Element('citeData', property="http://purl.org/dc/terms/title", use="head/@n")
            cs.append(cite_data)
            
            webview_data = etree.Element('citeData', property="https://schema.org/url", use="@data-webview")
            cs.append(webview_data)

            child = deepest_div_path(d, is_top_level=False)
            if child is not None:
                cs.append(child)
            return cs
        # If no divs, look for paragraphs
        ps = [el for el in parent if el.tag.endswith('p')]
        if ps:
            if is_top_level:
                cs = etree.Element('citeStructure', unit='paragraph', match='p', use='@xml:id')
                
                webview_data = etree.Element('citeData', property="https://schema.org/url", use="@data-webview")
                cs.append(webview_data)
            else:
                cs = etree.Element('citeStructure', unit='paragraph', match='p', use='@xml:id', delim=":")
                
                webview_data = etree.Element('citeData', property="https://schema.org/url", use="@data-webview")
                cs.append(webview_data)
            return cs
        return None

    # Build refsDecl for logical_structure
    refsDecl = etree.Element('refsDecl', nsmap={None: 'http://www.tei-c.org/ns/1.0'})
    refsDecl.attrib['default'] = 'true'
    refsDecl.attrib['n'] = 'logical_structure'
    cs = deepest_div_path(body, is_top_level=True)
    if cs is not None:
        refsDecl.append(cs)
    return refsDecl

def inject_dynamic_refsdecl(tree):
    tei_encDesc = tree.xpath("/tei:TEI/tei:teiHeader/tei:encodingDesc", namespaces=NS)
    if not tei_encDesc:
        return tree
    tei_encDesc = tei_encDesc[0]
    # Remove existing refsDecls
    for el in tei_encDesc.findall(".//tei:refsDecl", namespaces=NS):
        tei_encDesc.remove(el)
    # Add dynamic refsDecl
    refs_logical = analyze_body_structure_and_build_citestructure(tree)
    if refs_logical is not None:
        tei_encDesc.append(refs_logical)
    # Add all_paragraphs refsDecl
    refs_all_pars = etree.XML('''
        <refsDecl xmlns="http://www.tei-c.org/ns/1.0" n="all_paragraphs">
            <citeStructure unit="paragraph" match="//div/p" use="@xml:id">
                <citeData property="https://schema.org/url" use="@data-webview"/>
            </citeStructure>
        </refsDecl>
    ''')
    tei_encDesc.append(refs_all_pars)
    # Always add published_page refsDecl
    refs_pages = etree.XML('''
        <refsDecl xmlns="http://www.tei-c.org/ns/1.0"
                    n="published_page">
            <citeStructure unit="page" match="//pb" use="@xml:id">
                <citeData property="https://schema.org/url" use="@data-webview"/>
            </citeStructure>
        </refsDecl>
    ''')
    tei_encDesc.append(refs_pages)
    # Add all_notes refsDecl
    refs_all_notes = etree.XML('''
        <refsDecl xmlns="http://www.tei-c.org/ns/1.0" n="all_notes">
            <citeStructure unit="note" match="//note" use="@xml:id">
                <citeData property="https://schema.org/url" use="@data-webview"/>
            </citeStructure>
        </refsDecl>
    ''')
    tei_encDesc.append(refs_all_notes)
    return tree



def create_root_collection(catalog_root, source_root, base_identifier):

    first_tei = next(source_root.glob("s01/s01-ed.xml"))
    print(f"Using {first_tei} to extract collection title")

    collection_title = extract_root_series_title(first_tei)

    collection = etree.Element(
        "collection",
        identifier=base_identifier
    )

    title = etree.SubElement(collection, "title")
    title.text = collection_title

    dublin = etree.SubElement(collection, "dublinCore")

    creator = etree.SubElement(dublin, "creator")
    creator.text = "Heinrich Wölfflin"

    language = etree.SubElement(dublin, "language")
    language.text = "de"

    members = etree.SubElement(collection, "members")

    for folder in sorted(source_root.iterdir()):
        if folder.is_dir() and folder.name.startswith("s"):
            etree.SubElement(
                members,
                "collection",
                filepath=f"./{folder.name}.xml"
            )

    tree = etree.ElementTree(collection)

    write_xml_with_schema(
        tree,
        catalog_root / "collection.xml"
    )


def create_subcollection(catalog_root, source_folder, output_root, base_identifier):

    volume_id = source_folder.name
    identifier = f"{base_identifier}/{volume_id}"

    subcollection = etree.Element(
        "collection",
        identifier=identifier
    )

    first_tei = next(source_folder.glob("*.xml"))
    titles = extract_volume_titles(first_tei)

    for t in titles:
        el = etree.SubElement(subcollection, "title")
        el.text = t

    members = etree.SubElement(subcollection, "members")

    tei_target_dir = output_root / volume_id
    tei_target_dir.mkdir(parents=True, exist_ok=True)

    for tei_file in sorted(source_folder.glob("*.xml")):
        name = tei_file.stem
        short = name.split("-")[-1]

        resource_identifier = f"{identifier}/{short}"
        target_file = tei_target_dir / tei_file.name

        tree = parse_xml(tei_file)

        tree = inject_webview_urls(tree, tei_file.name)
        tree = inject_dynamic_refsdecl(tree)

        tree.write(
            target_file,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        )

        resource = etree.SubElement(
            members,
            "resource",
            identifier=resource_identifier,
            filepath=f"../../tei/hwgw-edition/{volume_id}/{tei_file.name}" # e.g. ../../tei/hwgw-edition/s01/s01-ed.xml
        )

        # Extract <title level="m"> for resource title
        titles = tree.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@level='m']", namespaces=NS)
        for t in titles:
            title = etree.SubElement(resource, "title")
            if t.text:
                title.text = t.text.strip()

        # Add dublinCore metadata
        dublin = etree.SubElement(resource, "dublinCore")

        for author in extract_authors(tei_file):
            creator_el = etree.SubElement(dublin, "creator", xmlns="http://purl.org/dc/terms/")
            creator_el.text = author

        for editor in extract_editors(tei_file):
            editor_el = etree.SubElement(dublin, "editor", xmlns="http://purl.org/dc/terms/")
            editor_el.text = editor

        for publisher in extract_publishers(tei_file):
            publisher_el = etree.SubElement(dublin, "publisher", xmlns="http://purl.org/dc/terms/")
            publisher_el.text = publisher

        for date in extract_dates(tei_file):
            date_el = etree.SubElement(dublin, "date", xmlns="http://purl.org/dc/terms/")
            date_el.text = date

        for lang in extract_languages(tei_file):
            lang_el = etree.SubElement(dublin, "language", xmlns="http://purl.org/dc/terms/")
            lang_el.text = lang

        for license_text in extract_license(tei_file):
            rights_el = etree.SubElement(dublin, "rights", xmlns="http://purl.org/dc/terms/")
            rights_el.text = license_text

        for series_title in extract_series(tei_file):
            ispartof_el = etree.SubElement(dublin, "isPartOf", xmlns="http://purl.org/dc/terms/")
            ispartof_el.text = series_title


    tree = etree.ElementTree(subcollection)

    write_xml_with_schema(
        tree,
        catalog_root / f"{volume_id}.xml"
    )


# CLI

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--catalog", required=True)
    parser.add_argument("--inputFolder", required=True)
    parser.add_argument("--outputFolder", required=True)
    parser.add_argument("--baseIdentifier", default="https://example.org/dts/collections/hwgw")

    args = parser.parse_args()

    catalog_root = Path(args.catalog)
    source_root = Path(args.inputFolder)
    output_root = Path(args.outputFolder)

    catalog_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    create_root_collection(
        catalog_root,
        source_root,
        args.baseIdentifier
    )

    for folder in sorted(source_root.iterdir()):
        if folder.is_dir() and folder.name.startswith("s"):
            create_subcollection(
                catalog_root,
                folder,
                output_root,
                args.baseIdentifier
            )

    print("DTS data successfully generated.")


if __name__ == "__main__":
    main()
