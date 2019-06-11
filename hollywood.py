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
    while depht <= MAX_DEPHT:
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
            break
        elif depht > MAX_DEPHT:
            logging.error("Max depht reached! Aborting research.")
            break
        else:
            depht += 1
    return result


def main(args):
    actor1 = "\"{}\"".format(args["actor1"])
    actor2 = "\"{}\"".format(args["actor2"])
    
    query_actors = dbpedia_query(PREFIXES,
        """
        SELECT ?actor1 ?actor2 WHERE {{
        ?actor1 foaf:name {}@en.
        ?film1 dbpo:starring ?actor1.
        ?actor2 foaf:name {}@en.
        ?film2 dbpo:starring ?actor2. }} LIMIT 1""".format(actor1,actor2))["results"]["bindings"]
    if not query_actors:
        logging.error("Unfortunately DBpedia did not recognize one of the actors you suggested")
        return 1
    actor1_res = query_actors[0]["actor1"]["value"]
    actor2_res = query_actors[0]["actor2"]["value"]
    
    result = genealogy_research(actor1_res, actor2_res)
    if not result:
        print("Unable to find any direct genealogy")
    else:
        for r in result:
            rlen = len(r)
            if rlen > 1:
                for i in range(1, rlen):
                    a1 = actor1_res if i == 1 else r["actor{}".format(i-1)]["value"]
                    a2 = actor2_res if i == rlen-1 else r["actor{}".format(i)]["value"]
                    f = r["film{}".format(i-1)]["value"]
                    print("{} starred with {} in {}".format(
                        a1, a2, f).replace("http://dbpedia.org/resource/", ":"))
            else:
                print("{} starred with {} in {}".format(
                        actor1_res, actor2_res, 
                        r["film0"]["value"]).replace("http://dbpedia.org/resource/", ":"))
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Actors Genealogy query machine! Powered with DBpedia knowledge")
    parser.add_argument("actor1", nargs="?", default="Orson Welles")
    parser.add_argument("actor2", nargs="?", default="Jack Nicholson")
    arguments = vars(parser.parse_args())
    sys.exit(main(arguments))