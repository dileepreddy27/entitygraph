"""Optional real integrations, imported only when explicitly selected."""
from .pipeline import stable_id


class ModelExtractor:
    name = "huggingface-ner"

    def __init__(self, model="dslim/bert-base-NER", revision="main"):
        from transformers import AutoTokenizer, pipeline
        # Fast tokenizers use Hugging Face Tokenizers. Overflow windows avoid truncating documents.
        tokenizer = AutoTokenizer.from_pretrained(model, revision=revision, use_fast=True)
        if not tokenizer.is_fast:
            raise ValueError("a fast tokenizer is required")
        self.ner = pipeline("token-classification", model=model, revision=revision,
                            tokenizer=tokenizer, aggregation_strategy="simple", stride=64, device=-1)
        self.name = f"huggingface:{model}@{revision}"

    def extract(self, text):
        return [dict(label=e["entity_group"], text=text[e["start"]:e["end"]],
                     start=e["start"], end=e["end"], score=float(e["score"])) for e in self.ner(text)]


def resolve_spark(mentions):
    from pyspark.sql import SparkSession, functions as F
    if not mentions:
        return []
    spark = SparkSession.builder.appName("EntityGraph").getOrCreate()
    try:
        rows = spark.createDataFrame([(m["label"], m["key"], m["canonical"]) for m in mentions],
                                     ["label", "key", "canonical"])
        groups = rows.groupBy("label", "key").agg(F.min("canonical").alias("name")).collect()
        return [dict(id=stable_id(r.label, r.key), label=r.label, key=r.key, name=r.name)
                for r in sorted(groups, key=lambda r: (r.label, r.key))]
    finally:
        spark.stop()


def write_neo4j(graph, uri, user, password):
    from neo4j import GraphDatabase
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            for label in ["Document", "Entity", "Mention", "Transaction"]:
                session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE").consume()
            session.execute_write(_write_graph, graph)


def _write_graph(tx, graph):
    # All user-controlled values are parameters; replay is idempotent for identical input.
    queries = [
        ("documents", "UNWIND $rows AS r MERGE (n:Document {id:r.id}) SET n += r"),
        ("entities", "UNWIND $rows AS r MERGE (n:Entity {id:r.id}) SET n += r"),
        ("mentions", "UNWIND $rows AS r MATCH (d:Document {id:r.document_id}), (e:Entity {id:r.entity_id}) MERGE (m:Mention {id:r.id}) SET m += r MERGE (d)-[:HAS_MENTION]->(m) MERGE (m)-[:RESOLVES_TO]->(e)"),
        ("transactions", "UNWIND $rows AS r MATCH (d:Document {id:r.document_id}), (s:Entity {id:r.source_id}), (t:Entity {id:r.target_id}) MERGE (p:Transaction {id:r.id}) SET p += r MERGE (d)-[:EVIDENCES]->(p) MERGE (s)-[:PAYER]->(p) MERGE (p)-[:PAYEE]->(t)")]
    for key, query in queries:
        tx.run(query, rows=graph[key]).consume()
