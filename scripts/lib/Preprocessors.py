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
    preprocessedContent = preprocessor.preprocess(content)

"""

import re
import copy
from abc import ABC, abstractmethod
# from lib.DateUtils import extractXsdDate
# from organise_files import load_mapping
import xml.etree.ElementTree as ET
import xml.dom.minidom

class Preprocessor(ABC):
    @abstractmethod
    def preprocess(self, content: str) -> str:
        pass

class BasePreprocessor(Preprocessor):

    PREFIX = 'preprocessed_'

    def preprocess(self, content: str, module: str) -> str:
        """
        Common preprocessing steps that are shared across all modules.
        """

        # content = content.replace('xmlns="https://schema.easydb.de/EASYDB/1.0/objects/"', '') # remove easydb namespace
        root = self.processWikidataIdentifiers(content)
        return self.dumpXML(root)
    
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
    
    
class Preprocessors:
    @staticmethod
    def getPreprocessor(module: str) -> Preprocessor:
        """
        Returns the appropriate preprocessor based on the module name.
        """
        return BasePreprocessor()