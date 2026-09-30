import json
import tempfile
import unittest
from pathlib import Path
from entitygraph.pipeline import BaselineExtractor, alias_index, load_documents, run
from entitygraph.report import render


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(Path("fixtures/aliases.json").read_text())
        self.docs = load_documents("fixtures/documents.jsonl")
        self.extractor = BaselineExtractor(self.config)

    def test_fixture_graph_and_provenance(self):
        graph = run(self.docs, self.config, self.extractor)
        self.assertEqual(len(graph["entities"]), 8)
        self.assertEqual(len(graph["transactions"]), 2)
        self.assertEqual({t["amount"] for t in graph["transactions"]}, {"12500", "8000"})
        docs = {d["id"]: d["text"] for d in self.docs}
        for m in graph["mentions"]:
            self.assertEqual(docs[m["document_id"]][m["start"]:m["end"]], m["text"])
        northstar = [m for m in graph["mentions"] if m["canonical"] == "Northstar Analytics"]
        self.assertEqual(len({m["entity_id"] for m in northstar}), 1)
        self.assertIn("Northstar Analytics Inc.", {m["text"] for m in northstar})

    def test_deterministic_replay(self):
        first = run(self.docs, self.config, self.extractor)
        second = run(self.docs, self.config, self.extractor)
        self.assertEqual(first, second)
        self.assertEqual(len({m["id"] for m in first["mentions"]}), len(first["mentions"]))

    def test_no_invented_transactions_or_unknown_entities(self):
        g = run([{"id": "test", "text": "Harbor Systems discussed Northstar Analytics. Unknown Corp paid nobody."}], self.config, self.extractor)
        self.assertEqual(g["transactions"], [])
        self.assertEqual(len(g["entities"]), 2)

    def test_word_boundaries(self):
        self.assertEqual(self.extractor.extract("Bostonian Cedar LabsExtra"), [])

    def test_alias_conflict(self):
        with self.assertRaises(ValueError):
            alias_index({"ORG": {"A": ["same"], "B": ["SAME"]}})

    def test_bad_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.jsonl"
            for body in ['not json', '{"id":"x","text":4}', '{"id":"x","text":""}\n{"id":"x","text":""}']:
                path.write_text(body)
                with self.assertRaisesRegex(ValueError, "line"):
                    load_documents(path)

    def test_html_escapes_sources(self):
        g = run([{"id":"<script>", "text":"<script>alert(1)</script>"}], self.config, self.extractor)
        html = render(g)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_type_is_part_of_identity(self):
        from entitygraph.pipeline import resolve_local
        entities = resolve_local([dict(label=l, key="paris", canonical="Paris") for l in ["PER", "LOC"]])
        self.assertNotEqual(entities[0]["id"], entities[1]["id"])

    def test_empty(self):
        self.assertEqual(run([], self.config, self.extractor)["entities"], [])


if __name__ == "__main__":
    unittest.main()
