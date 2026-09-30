"""Run explicitly against a disposable Neo4j database; never a production graph."""
import json
import os
from pathlib import Path
from neo4j import GraphDatabase
from entitygraph.adapters import resolve_spark, write_neo4j
from entitygraph.pipeline import BaselineExtractor, load_documents, run

config = json.loads(Path("fixtures/aliases.json").read_text())
docs = load_documents("fixtures/documents.jsonl")
local = run(docs, config, BaselineExtractor(config))
distributed = run(docs, config, BaselineExtractor(config), resolve_spark)
assert local == distributed, "Spark and local graph differ"
uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
password = os.environ["NEO4J_PASSWORD"]
for _ in range(2):
    write_neo4j(local, uri, "neo4j", password)
with GraphDatabase.driver(uri, auth=("neo4j", password)) as driver:
    with driver.session() as session:
        for label, key in [("Entity", "entities"), ("Mention", "mentions"), ("Transaction", "transactions"), ("Document", "documents")]:
            count = session.run(f"MATCH (n:{label}) RETURN count(n) AS count").single()["count"]
            assert count == len(local[key]), (label, count)
        count = session.run("MATCH (:Document)-[:HAS_MENTION]->(:Mention)-[:RESOLVES_TO]->(:Entity) RETURN count(*) AS n").single()["n"]
        assert count == len(local["mentions"])
print("Spark parity, Neo4j replay, node counts, and mention lineage passed")
