"""
This file contains the Preprocessor classes for the different modules. It contains a function
that returns the appropriate preprocessor based on the module name.

The preprocess function in each preprocessor class takes the content of an input file as a string
and returns the preprocessed content as a string.

The preprocess function in the BasePreprocessor class contains the common preprocessing steps
that are shared across all modules. If no specific preprocessor is found for a module, the
BasePreprocessor is returned.

Usage:
    preprocessor = Preprocessors.getPreprocessor('Literature')
    preprocessedContent = preprocessor.preprocess(content, 'Literature')

"""

import re
import copy
from abc import ABC, abstractmethod
# from lib.DateUtils import extractXsdDate
# from organise_files import load_mapping
from lib.DateUtils import convertEDTFdate, normalize_object_date, parse_date_with_fallback
# from sariDateParser.dateParser import parse
try:
    from sariDateParser.dateParser import parse as legacy_parse  # type: ignore[import-not-found]
except ImportError:
    legacy_parse = None
import xml.etree.ElementTree as ET
import xml.dom.minidom

class Preprocessor(ABC):
    @abstractmethod
    def preprocess(self, content: str, module: str) -> str:
        pass

class BasePreprocessor(Preprocessor):

    PREFIX = 'preprocessed_'
    TEI_NAMESPACE = {'tei': 'http://www.tei-c.org/ns/1.0'}

    def preprocess(self, content: str, module: str) -> str:
        """
        Common preprocessing steps that are shared across all modules.
        """

        content = re.sub(r'\s+xmlns="[^"]*"', '', content)  # remove default xmlns declaration
        root = self.processWikidataIdentifiers(content)
        return self.dumpXML(root)

    def buildDateQualifier(self, normalized: dict) -> str:
        """
        Build a compact qualifier string to preserve date semantics for KG mapping.
        """
        qualifiers = []

        status = normalized.get('parse_status')
        precision = normalized.get('precision')
        if status == 'unknown' or precision == 'unknown':
            qualifiers.append('unknown')
        if precision == 'century':
            qualifiers.append('century-derived')
        if precision == 'range':
            qualifiers.append('range')
        if precision == 'open':
            qualifiers.append('open-interval')
        if precision == 'year' and not normalized.get('approximate') and not normalized.get('disjunction') and not normalized.get('uncertain'):
            qualifiers.append('exact-year')

        if normalized.get('approximate'):
            qualifiers.append('approximate')
        if normalized.get('disjunction'):
            qualifiers.append('alternative-years')
        if normalized.get('uncertain'):
            qualifiers.append('uncertain')
        if normalized.get('bce'):
            qualifiers.append('bce')

        # Preserve order and uniqueness.
        unique = []
        for q in qualifiers:
            if q not in unique:
                unique.append(q)
        return '|'.join(unique)

    def processTEIDateElements(self, root: ET.Element) -> ET.Element:
        """
        Add sibling preprocessed_date/preprocessed_birth/preprocessed_death elements
        while leaving original date-bearing elements untouched.
        """
        namespaced_elements = []
        for tag in ('date', 'birth', 'death'):
            namespaced_elements.extend(root.findall(f'.//tei:{tag}', self.TEI_NAMESPACE))

        elements = namespaced_elements
        if not elements:
            for tag in ('date', 'birth', 'death'):
                elements.extend(root.findall(f'.//{tag}'))

        namespace_uri = None
        if root.tag.startswith('{') and '}' in root.tag:
            namespace_uri = root.tag[1:].split('}', 1)[0]

        for date_elem in elements:
            text_value = (date_elem.text or '').strip()
            when_value = (date_elem.get('when') or '').strip()
            raw_value = text_value or when_value
            if not raw_value:
                continue

            normalized = normalize_object_date(raw_value)

            local_name = date_elem.tag.split('}', 1)[-1] if '}' in date_elem.tag else date_elem.tag
            preprocessed_name = f'preprocessed_{local_name}'
            preprocessed_tag = f'{{{namespace_uri}}}{preprocessed_name}' if namespace_uri else preprocessed_name
            preprocessed_elem = ET.Element(preprocessed_tag)
            preprocessed_elem.text = raw_value

            if normalized['lower']:
                preprocessed_elem.set(f'{self.PREFIX}dateLower', normalized['lower'])
            if normalized['upper']:
                preprocessed_elem.set(f'{self.PREFIX}dateUpper', normalized['upper'])

            qualifier = self.buildDateQualifier(normalized)
            if qualifier:
                preprocessed_elem.set(f'{self.PREFIX}dateQualifier', qualifier)

            parent = self.getParentOf(date_elem, root)
            if parent is not None:
                index = list(parent).index(date_elem)
                parent.insert(index + 1, preprocessed_elem)

        return root
    
    def strip_whitespace(self, elem):
        """Recursively remove whitespace-only text"""
        if elem.text is not None and elem.text.strip() == "":
            elem.text = None
        if elem.tail is not None and elem.tail.strip() == "":
            elem.tail = None
        for child in elem:
            self.strip_whitespace(child)

    def dumpXML(self, root: ET.Element) -> str:
        """
        Return the XML content as a pretty-printed string.
        """
        self.strip_whitespace(root)
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = xml.dom.minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        pretty_xml = "\n".join([line for line in pretty_xml.split('\n') if line.strip()]) # Remove empty lines
        return pretty_xml
    
    def processWikidataIdentifiers(self, content: str) -> ET.Element:
        """"
        This function searches for occurrences of 'https://www.wikidata.org/wiki/' 
        in the text of XML elements within the provided content. If found, it replaces it 
        with 'https://www.wikidata.org/entity/'.
        """
        root = self.parseXML(content)
        for elem in root.iter():
            if elem.text and 'https://www.wikidata.org/wiki/' in elem.text:
                elem.text = elem.text.replace('https://www.wikidata.org/wiki/', 'https://www.wikidata.org/entity/')
        return root
    
    def getParentOf(self, element: ET.Element, root: ET.Element) -> ET.Element:
        """
        Find the parent of a given element in the XML tree.
        """
        for parent in root.iter():
            for child in parent: # make sure it's direct child
                if child is element:
                    return parent
        return None

    def parseXML(self, content: str) -> ET.Element:
        """
        Parse the XML content and return the root element.
        """
        return ET.fromstring(content)
    
    
    def processDateFields(self, root: ET.Element, dateFieldSelectors: list) -> ET.Element:
        """
        This function takes an XML root element and a list of field selectors that contain dates.
        It parses the date values and adds the lower and upper date values to the XML element.
        """
        for dateFieldSelector in dateFieldSelectors:
            datafields = root.findall(dateFieldSelector)
            for datafield in datafields:
                value_node = datafield.find('value')
                value = value_node.text if value_node is not None else datafield.text
                if value is None:
                    continue
                parsedDate = None
                if legacy_parse is not None:
                    parsedDate = legacy_parse(value)
                else:
                    parsedDate = parse_date_with_fallback(value)
                if parsedDate is not None:
                    daterange = convertEDTFdate(parsedDate)
                    datafield.set(f'{self.PREFIX}type', 'daterange')
                    datafield.set(f'{self.PREFIX}dateLower', daterange['lower'])
                    datafield.set(f'{self.PREFIX}dateUpper', daterange['upper'])
        return root
    
    def processYearFields(self, root: ET.Element, yearFieldSelectors: list) -> ET.Element:
        """
        This function takes an XML root element and a list of field selectors that contain years.
        If necessary, it converts the year fields into a xsd:gYear compliant format. e.g. at least
        4 digits and optionally prefixed with a '-' sign for BCE years.
        """
        for yearFieldSelector in yearFieldSelectors:
            datafields = root.findall(yearFieldSelector)
            for datafield in datafields:
                value_node = datafield.find('value')
                value = value_node.text if value_node is not None else datafield.text
                if value is not None:
                    value = value.strip()
                    if re.fullmatch(r'-?\d+', value):
                        year_value = int(value)
                        if year_value < 0:
                            processedValue = f'-{abs(year_value):05}'
                        else:
                            processedValue = f'{year_value:04}'
                        datafield.set(f'{self.PREFIX}type', 'gYear')
                        datafield.set(f'{self.PREFIX}year', processedValue)
        return root


class DatePreprocessor(BasePreprocessor):
    """
    Preprocessor for modules that contain date-bearing TEI elements.
    """

    def preprocess(self, content: str, module: str) -> str:
        content = super().preprocess(content, module)
        root = super().parseXML(content)
        root = super().processTEIDateElements(root)
        return super().dumpXML(root)
    
class Preprocessors:
    @staticmethod
    def getPreprocessor(module: str) -> Preprocessor:
        """
        Returns the appropriate preprocessor based on the module name.
        """
        if module in ('objects', 'persons'):
            return DatePreprocessor()
        return BasePreprocessor()