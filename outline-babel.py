#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: Jonathan Cervidae <jonathan.cervidae@gmail.com>
# PGP Fingerprint: 2DC0 0A44 123E 6CC2 EB55  EAFB B780 421F BF4C 4CB4
# Last changed: $LastEdit: 2009-06-06 13:05:02 BST$
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import logging as logging_module

import lxml.etree
import zipfile
import random
from StringIO import StringIO
import copy
import optparse

logger = logging_module.getLogger("outline-babel")

# This spec is not flexible enough and should support multiple-file project
# inputs. I have no need of this support right now but will change the
# specification of the Parser and Writer classes to support them when it
# becomes necessary.

# You should inherit your parsers from here. You can assume you will only be
# passed file-like objects representing your outliner type, and you should
# override the method build_tree with a method that constructs a tree in the
# fashion described by that methods docstring.
# You must override the name attribute with the name of your parser. You must
# call super on the original __init__ method if you override it and it wil
# usually make sense to do it as the first line of your own __init__.
#
# Do not call super on any other method.

class OutlineParser(object):
    name = NotImplementedError
    @staticmethod
    def could_this_be_you(input):
        """You must override this method with a predicate that returns either True or
False. input is a a file-like object which you can assume to have it's
file-pointer (if it has one) set at position 0. You must return True if this
type of file-like object could be the format you parse and False if not."""
        raise NotImplementedError
    def __init__(self, input):
        """Parses outliner. input should be a file-like object. """
        self.input = input
        self.tree = {}
        self.build_tree()
    def build_tree(self):
        """This function must modify a dictionary tree from the file-like object on
self.input. You can assume it will be set at file pointer position 0 if it
supports seeking. The dictionary it must modify is self.tree. Into this
dictionary, the branches of the outliner are inserted into the dictionary as
another dictionary. The leaves are inserted into a branch dictionary with
their name as the key and True as their value. You will usually do this by
calling this method recursively from itself."""
        raise NotImplementedError
# You must inherit your writers from here. You must override the write method
# with a method that creates an outliner in your format. You must also
# overwrite the name property with the name of your writer and extension with
# the file extension of your outliner file. You must call super on the
# original __init__ method if you override it and it wil usually make sense to
# do it as the first line of your own __init__. Do not call super on any other
# method.

class OutlineWriter(object):
    name = NotImplementedError
    extension = NotImplementedError
    def __init__(self, output, tree):
        """Creates an outliner file. output should be an empty file-like
        object with the file pointer at the beginning.

        tree: This is a tree of the fashion described by the docstring of
        OutlineParser.build_tree. You must write to the file-like object
        passed in as output a suitable representation of this tree for your
        outliner.  """
        self.output = output
        self.tree = tree
    def write(self):
        """You must override this method with a writer that writes the
        outliner file to the file-like object on self.output. The tree to
        build it from is available on self.tree and is in the format described
        by the docstring of OutlineParser.build_tree"""
        raise NotImplementedError


class VYMParser(OutlineParser):
    name ="vym"
    @staticmethod
    def could_this_be_you(input):
        global logger
        it_could = False
        try:
            zip = zipfile.ZipFile(input)
        except:
            logger.debug(
                "It can't be me because it's not a zip file" %
                ( str(klass), args[0] )
            )
            return False
        logger.debug("Zip file, could still be me")
        for name in zip.namelist():
            last_four = name[-4:].lower()
            logger.debug("Checking %s against %s" % ( name, last_four) )
            if last_four == ".xml":
                logger.debug("We match, looking for doctype")
                doc = lxml.etree.parse(StringIO(zip.read(name)))
                logger.debug("Doctype is %s" % doc.docinfo.doctype )
                return doc.docinfo.doctype == '<!DOCTYPE vymmap>'
        return False
    def build_tree(self):
        zip = zipfile.ZipFile(self.input)
        doc_path = None
        for name in zip.namelist():
            if name[-4:].lower() == ".xml":
                doc_path = name
                break
        if not doc_path:
            raise StandardError, "This is not a vym file"
        doc = lxml.etree.parse(StringIO(zip.read(name)))
        root = doc.getroot()
        mapcenter = root.find("mapcenter")
        self._recursive_build_tree(self.tree, mapcenter.findall("branch") )
    def _recursive_build_tree(self, branch, elements):
        for element in elements:
            heading = element.find("heading")
            name = heading.text
            sub_branches = element.findall("branch")
            if len(sub_branches) > 0:
                branch[name] = sub_branch = {}
                self._recursive_build_tree(sub_branch, sub_branches)
            else:
                branch[name] = True

class KPlatoParser(OutlineParser):
    name = "kplato"
    @staticmethod
    def could_this_be_you(input):
        try:
            zip = zipfile.ZipFile(input)
        except:
            return False
        if not "maindoc.xml" in zip.namelist():
            return False
        doc = self.main_doc_from_zip(zip)
        return doc.docinfo.doctype == '<!DOCTYPE kplato>'
    @staticmethod
    def main_doc_from_zip(zip):
        # TODO: You can do this without StringIO
        return lxml.etree.parse(StringIO(zip.read("maindoc.xml")))
    def build_tree(self):
        zip = zipfile.ZipFile(self.input)
        doc = self.main_doc_from_zip(zip)
        root = doc.getroot()
        project = root.find("project")
        self._recursive_build_tree( self.tree, project.findall("task") )

    def _recursive_build_tree(self, branch, elements):
        for element in elements:
            name = element.get("name")
            sub_tasks = element.findall("task")
            if len(sub_tasks) > 0:
                branch[name] = sub_branch = {}
                self._recursive_build_tree(sub_branch, sub_tasks)
            else:
                branch[name] = True

class XMindWriter(OutlineWriter):
    extension = name = "xmind"
    def __init__(self, output, tree):
        super(XMindWriter, self).__init__(output, tree)
        self.used_ids = {}
    def xmind_id(self):
        # I have no idea if the fact the first part is always a number is
        # significant so let's assume it is and refuse to re-use the rest of
        # the string with a different number (i don't think it is but this
        # doesn't hurt)
        import random
        number = random.choice('1234567890')
        rest = ''
        for i in range(26):
            rest += random.choice('qwertyuiopasdfghjklzxcvbnm1234567890')
        # If infinite monkeys on infinite typewriters wrote a forever loop...
        if rest in self.used_ids:
            return self.xmind_id()
        self.used_ids[rest] = True
        return {'id': number + rest }

    def write(self):
        #zi.compress_type = zipfile.ZIP_DEFLATED
        zip = zipfile.ZipFile(self.output, "w")
        zi = zipfile.ZipInfo("meta.xml")
        zi.external_attr = 0644 << 16L
        zip.writestr(
            zi,
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            '<meta xmlns="urn:xmind:xmap:xmlns:meta:2.0" version="2.0"/>'
        )
        zi = zipfile.ZipInfo("META-INF/manifest.xml")
        zi.external_attr = 0644 << 16L
        zip.writestr(
            zi,
            """<?xml version="1.0" encoding="utf-8" standalone="no"?>
<manifest xmlns="urn:xmind:xmap:xmlns:manifest:1.0">
  <file-entry full-path="content.xml" media-type="text/xml" />
  <file-entry full-path="META-INF/" media-type="" />
  <file-entry full-path="META-INF/manifest.xml"
  media-type="text/xml" />"""
        )

        # Now we do the actual map!
        doc = lxml.etree.parse(StringIO('<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0" xmlns:fo="http://www.w3.org/1999/XSL/Format" xmlns:svg="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink" version="2.0"/>'))
        content = doc.getroot()
        sheet = lxml.etree.Element('sheet', self.xmind_id())
        content.append(sheet)
        topic = lxml.etree.Element('topic', self.xmind_id())
        sheet.append(topic)
        title = lxml.etree.Element('title')
        title.text = "Exported Sheet"
        sheet.append(title)
        title = lxml.etree.Element('title')
        title.text = "Exported"
        topic.append(title)
        children = lxml.etree.Element('children')
        topics = lxml.etree.Element('topics', { 'type': 'attached' })
        children.append(topics)
        topic.append(children)
        self.build_xml(topics, self.tree)
        xml = '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n'
        zi = zipfile.ZipInfo("content.xml")
        zi.external_attr = 0644 << 16L
        zip.writestr(
            zi,
            '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n' +
            lxml.etree.tostring(
                doc,method="xml",xml_declaration=None,
                pretty_print=True, with_tail=True
            )
        )
        zip.close()

    def build_xml(self, node, dictionary):
        for key, value in dictionary.items():
            topic = lxml.etree.Element('topic', self.xmind_id())
            node.append(topic)
            title = lxml.etree.Element('title')
            title.text = key
            topic.append(title)
            if value is not True:
                children = lxml.etree.Element('children')
                topic.append(children)
                topics = lxml.etree.Element('topics', { 'type': 'attached' })
                children.append(topics)
                self.build_xml(topics, value)


if __name__ == '__main__':
    usage = (
"""%prog [options] <input file> [<output file>]

This program converts from one outline format to another. It will detemine
which output format to use based on the extention of your output file.
Currently supported are:

Input:
"""
    )
    for klass in OutlineParser.__subclasses__():
        usage += ( klass.name + os.linesep )
    usage += "%sOutput:%s" % ( os.linesep, os.linesep )
    for klass in OutlineWriter.__subclasses__():
        usage += ( klass.name + os.linesep )
    usage = usage.rstrip()
    version="%prog 0.1.2"
    parser = optparse.OptionParser(usage=usage,version=version)
    # TODO: Option to force input format
    # TODO: Dump should not necessarily not write an output file.
    parser.add_option(
        "-d", "--dump", action="store_true", dest="dump", default=False,
        help="Will dump the parsed input tree instead of writing it to an"
             "to an output file"
    )
    parser.add_option(
        "-v", "--verbose", action="store_true", dest="verbose", default=False,
        help="Makes the program more chatty"
    )
    parser.add_option(
        "--debug", action="store_true", dest="debug", default=False,
        help="Makes the program display info useful to it's developers"
    )

    options, args = parser.parse_args()
    expected_number_of_args = 2
    if options.dump:
        expected_number_of_args = 1
    if len(args) != expected_number_of_args:
        parser.error("incorrect number of arguments")

    logger.addHandler(logging_module.StreamHandler(sys.stderr))
    if options.verbose:
        logger.setLevel(logging_module.INFO)
    else:
        logger.setLevel(logging_module.WARNING)
    if options.debug:
        logger.setLevel(logging_module.DEBUG)

    input = open(args[0] ,"r")
    parsing_class = None
    # TODO: Just picks first matching parser. This is only OK because current
    # parsers could never both return true on the same file unless it was
    # meddled with other than by the proper applications. If a parser is ever
    # added which could produce multiple matches then we will need to be a bit
    # more intelligent.
    logger.debug( "Asking parsers if they can parse %s" % args[0] )
    for klass in OutlineParser.__subclasses__():
        logger.debug(
            "%s%s:%s" %
            ( os.linesep, str(klass), os.linesep )
        )
        input.seek(0,0)
        if klass.could_this_be_you(input):
            logger.debug( "I can parse this file." )
            parsing_class = klass
            break
        else:
            logger.debug( "I cannot parse this file." )
    if not parsing_class:
        logger.error(
            "I could not work out what type of file %s is." % \
            args[0]
        )
        sys.exit(1)
    parser = parsing_class(input)
    if options.dump:
        from pprint import pprint
        pprint(parser.tree)
        sys.exit(0)
    # FIXME: More than just xmind should be supported
    writer = XMindWriter(open(args[1],"w"),parser.tree)
    writer.write()

