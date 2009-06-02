#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: Jonathan Cervidae <jonathan.cervidae@gmail.com>
# PGP Fingerprint: 2DC0 0A44 123E 6CC2 EB55  EAFB B780 421F BF4C 4CB4
# Last changed: $LastEdit: 2009-06-01 21:17:01 BST$

import sys
import os

def eprint(string):
    sys.stderr.write(str(string) + os.linesep)

if len(sys.argv) != 2:
    eprint("Usage: %s <dir-to-create>%s", (sys.argv[0]))
    sys.exit(1)

dir = sys.argv[1]

# Insecure, do it in your home dir somewhere...
if os.path.exists(dir):
    eprint(
        "Already exists %s, delete it first or choose somewhere else." %
        (dir,)
    )
    sys.exit(2)

import lxml.etree
doc = lxml.etree.parse("maindoc.xml")
root = doc.getroot()
project = root.find("project")

# Wow, etree is awesome and python doesn't whine about recursion, I love it!!!
def build_tree(tree, elements):
    for element in elements:
        name = element.get("name")
        sub_tasks = element.findall("task")
        if len(sub_tasks) > 0:
            tree[name] = sub_tree = {}
            build_tree(sub_tree, sub_tasks)
        else:
            tree[name] = True

tasks = {}
build_tree(tasks, project.findall("task"))

# So we can do it again :)
def build_path(path, dictionary):
    os.mkdir(path)
    for key, value in dictionary.items():
        sub_path = os.path.join(path, key)
        if value is True:
            open(sub_path,"w").close()
        else:
            build_path(sub_path, value)

build_path(dir, tasks)
