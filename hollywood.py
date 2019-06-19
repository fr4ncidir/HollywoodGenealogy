#!/usr/bin python3
# -*- coding: utf-8 -*-
#
#  hollywood.py
#  
#  Copyright 2019 Francesco Antoniazzi <francesco.antoniazzi1991@gmail.com>
#  
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#  
#  

import requests
import json
import sys
import argparse
import logging
from urllib.parse import quote_plus
from rdflib import URIRef

PREFIXES = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX : <http://dbpedia.org/resource/>
PREFIX dbpedia2: <http://dbpedia.org/property/>
PREFIX dbpedia: <http://dbpedia.org/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dbpo: <http://dbpedia.org/ontology/>
"""

MAX_DEPHT = 10
ENDPOINT_ADDRESS = "http://dbpedia.org/sparql?default-graph-uri=http%3A%2F%2Fdbpedia.org&query={}&output=json"


def dbpedia_query(prefixes, sparql_query, address=ENDPOINT_ADDRESS):
    sparql = quote_plus("{} {}".format(prefixes, sparql_query))
    url = address.format(sparql)
    r = requests.get(url)
    if r.status_code != 200:
        r.raise_for_status()
    return json.loads(r.text)

def genealogy_research(actor1, actor2, n_alternatives=1):
    template = "?film{} dbpo:starring ?actor{}. ?film{} dbpo:starring ?actor{}."
    depht = 1
    while True:
        if depht > MAX_DEPHT:
            logging.error("Max depht reached! Aborting research.")
            return []
        sparql = "SELECT * WHERE {"
        lines = " ".join([ template.format(i,i,i,i+1) for i in range(depht) ])
        if n_alternatives >= 1:
            sparql = sparql + lines + "}} LIMIT {} ".format(n_alternatives)
        else:
            sparql = sparql + lines + "} "
        sparql = sparql.replace("?actor0", URIRef(actor1).n3()).replace("?actor{}".format(depht), URIRef(actor2).n3())
        logging.debug(sparql)
        
        result = dbpedia_query(PREFIXES,sparql)["results"]["bindings"]
        if result:
            logging.debug(result)
            return result
        else:
            depht += 1


def maybe_looking_for(actor,precision=4):
    if " " in actor:
        regex = actor.split()[0]
    else:
        regex = actor[0:min(precision,len(actor))]
    query_similar = dbpedia_query(PREFIXES,
        """
        SELECT DISTINCT ?actor_name WHERE {{
        ?actor foaf:name ?actor_name.
        ?film dbpo:starring ?actor.
        FILTER regex(?actor_name, '{}', 'i')
        }}
        """.format(regex))["results"]["bindings"]
    if not query_similar:
        print("DBpedia does not recognize {}".format(actor))
    else:
        print("Maybe you were looking for...")
        for suggestion in query_similar:
            print(suggestion["actor_name"]["value"])


def main(args):
    actor1 = "\"{}\"".format(args["actor1"])
    actor2 = "\"{}\"".format(args["actor2"])
    
    query_actors = dbpedia_query(PREFIXES,
        """
        SELECT ?actor1 ?actor2 WHERE {{
        OPTIONAL {{?actor1 foaf:name {}@en.
        ?film1 dbpo:starring ?actor1.}}
        OPTIONAL {{?actor2 foaf:name {}@en.
        ?film2 dbpo:starring ?actor2.}} }} LIMIT 1""".format(actor1,actor2))["results"]["bindings"]
    if "actor1" not in query_actors[0]:
        print("Unable to find {}.".format(actor1))
        maybe_looking_for(args["actor1"])
        return 1
    if "actor2" not in query_actors[0]:
        print("Unable to find {}.".format(actor2))
        maybe_looking_for(args["actor2"])
        return 1
    actor1_res = query_actors[0]["actor1"]["value"]
    actor2_res = query_actors[0]["actor2"]["value"]
    
    result = genealogy_research(actor1_res, actor2_res, int(args["alternatives"]))
    if not result:
        print("Unable to find any direct genealogy")
    else:
        logging.debug(result)
        for r in result:
            index = 0
            end_of_result = False
            while not end_of_result:
                a1 = actor1_res if index == 0 else r["actor{}".format(index)]["value"]
                f = r["film{}".format(index)]["value"]
                if "actor{}".format(index+1) in r:
                    a2 = r["actor{}".format(index+1)]["value"]
                else:
                    a2 = actor2_res
                    end_of_result = True
                print("({}) {} starred with {} in {}".format(
                        index, a1, a2, f).replace("http://dbpedia.org/resource/", ":"))
                index += 1
            print("")
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Actors Genealogy query machine! Powered with DBpedia knowledge")
    parser.add_argument("actor1", nargs="?", default="Orson Welles")
    parser.add_argument("actor2", nargs="?", default="Jack Nicholson")
    parser.add_argument("alternatives", nargs="?", default=1)
    arguments = vars(parser.parse_args())
    sys.exit(main(arguments))
