<!DOCTYPE HTML>
<html>
<body>

<?php 

define("prefixes", "PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX : <http://dbpedia.org/resource/>
PREFIX dbpedia2: <http://dbpedia.org/property/>
PREFIX dbpedia: <http://dbpedia.org/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dbpo: <http://dbpedia.org/ontology/> ", true);

define("max_depht", 10, true);

function dbpedia_query(string $sparql) {
    $params = array( 
        "default-graph-uri" => "http://dbpedia.org",
        "query" => prefixes . $sparql,
        "output" => "json"
    );
    
    $request = file_get_contents(
        "http://dbpedia.org/sparql" . "?" . http_build_query($params));
    
    return json_decode($request, TRUE);
}

function maybe_looking_for(string $name, int $precision=4) {
    if (strpos($name, " ") !== FALSE) {
        $regex = explode(" ", $name)[0];
    }
    else {
        $regex = substr($name, 0, min($precision, strlen($name)));
    }
    $query_similar = dbpedia_query(
        "SELECT DISTINCT ?actor_name WHERE {
        ?actor foaf:name ?actor_name.
        ?film dbpo:starring ?actor.
        FILTER regex(?actor_name, '" . $regex . "', 'i')}");
    #echo print_r($query_similar["results"]["bindings"]);
    if (array_key_exists("actor_name", $query_similar["results"]["bindings"][0]) === FALSE) {
        echo "DBpedia does not recognize " . $name . "<br>";
    }
    else {
        echo "<h2> Suggestions: </h2> <br>";
        foreach ($query_similar["results"]["bindings"] as &$value) {
            echo $value["actor_name"]["value"] . "<br>";
        }
    }
}

function genealogy_research(string $actor1, string $actor2, int $alternatives=1) {
    $template = "?film%d dbpo:starring ?actor%d. ?film%d dbpo:starring ?actor%d.";
    $depht = 0;
    do {
        $depht++;
        if ($depht > max_depht) {
            echo "<h2> Max depht reached! </h2> <br>";
            return array();
        }
        $accumulate = array();
        for ($i=0; $i<$depht; $i++) {
            array_push($accumulate, sprintf($template, $i, $i, $i, $i+1));
        }
        $sparql = "SELECT * WHERE {" . implode(" ", $accumulate) . "}";
        if ($alternatives >= 1) {
            $sparql = $sparql . " LIMIT " . $alternatives;
        }
        $sparql = str_replace("?actor0", "<" . $actor1 . ">", $sparql);
        $sparql = str_replace("?actor" . $depht , "<" . $actor2 . ">", $sparql);
        #print $sparql;
        
        $result = dbpedia_query($sparql)["results"]["bindings"];
    } while (empty($result));
    return $result;
}

$actor_1 = "'" . $_POST["actor1"] . "'";
$actor_2 = "'" . $_POST["actor2"] . "'";

$query_actors = dbpedia_query(
    "SELECT ?actor1 ?actor2 WHERE {
        OPTIONAL {?actor1 foaf:name " . $actor_1 . "@en.
        ?film1 dbpo:starring ?actor1.}
        OPTIONAL {?actor2 foaf:name " . $actor_2 . "@en.
        ?film2 dbpo:starring ?actor2.} } LIMIT 1");
#echo print_r($query_actors["results"]["bindings"][0]);

if (array_key_exists("actor1", $query_actors["results"]["bindings"][0]) === FALSE) {
    echo "<h1> Unable to find " . $_POST["actor1"] . "</h1> <br>";
    maybe_looking_for($_POST["actor1"]);
    return;
}
if (array_key_exists("actor2", $query_actors["results"]["bindings"][0]) === FALSE) {
    echo "<h1> Unable to find " . $_POST["actor2"] . "</h1> <br>";
    maybe_looking_for($_POST["actor2"]);
    return;
}
$actor_1_res = $query_actors["results"]["bindings"][0]["actor1"]["value"];
$actor_2_res = $query_actors["results"]["bindings"][0]["actor2"]["value"];

$result = genealogy_research($actor_1_res, $actor_2_res, $_POST["alternatives"]);

if (empty($result)) {
    echo "<h1> Unable to find direct genealogy </h1> <br>";
}
else {
    #print_r($result);
    foreach ($result as &$r) {
        $index = 0;
        $eor = FALSE;
        do {
            $a1 = ( $index === 0 ? $actor_1_res : $r["actor" . $index]["value"]);
            $f = $r["film" . $index]["value"];
            if (array_key_exists("actor" . strval($index+1), $r) === TRUE) {
                $a2 = $r["actor" . strval($index+1)]["value"];
            }
            else {
                $a2 = $actor_2_res;
                $eor = TRUE;
            }
            echo str_replace("http://dbpedia.org/resource/", ":", 
                "(" . $index . ") ". $a1 . " starred with " . $a2 . " in " . $f . "<br>");
            $index++;
        } while ($eor === FALSE);
    }
}
?>

</body>
</html>