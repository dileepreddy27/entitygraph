import argparse
import json
import os
import sys
from pathlib import Path
from .pipeline import BaselineExtractor, load_documents, run
from .report import render


def main():
    parser = argparse.ArgumentParser(description="Build an auditable entity graph from JSONL documents")
    parser.add_argument("--input", default="fixtures/documents.jsonl")
    parser.add_argument("--aliases", default="fixtures/aliases.json")
    parser.add_argument("--output", default="artifacts")
    parser.add_argument("--extractor", choices=["baseline", "model"], default="baseline")
    parser.add_argument("--model", default="dslim/bert-base-NER")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--resolver", choices=["local", "spark"], default="local")
    parser.add_argument("--neo4j", action="store_true")
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.aliases).read_text(encoding="utf-8"))
        extractor = BaselineExtractor(config)
        resolver = None
        if args.extractor == "model":
            from .adapters import ModelExtractor
            extractor = ModelExtractor(args.model, args.revision)
        if args.resolver == "spark":
            from .adapters import resolve_spark
            resolver = resolve_spark
        graph = run(load_documents(args.input), config, extractor, resolver)
        if args.neo4j:
            from .adapters import write_neo4j
            write_neo4j(graph, os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                        os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"])
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        (output / "graph.json").write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (output / "report.html").write_text(render(graph), encoding="utf-8")
        print(json.dumps({key: len(graph[key]) for key in ["documents", "mentions", "entities", "transactions"]}))
        return 0
    except (ValueError, OSError, KeyError, ImportError) as exc:
        print(f"EntityGraph: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
