"""Deterministic extraction, conservative resolution, and graph projection."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def stable_id(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[:24]


def normalize(value):
    return " ".join(re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFKC", value).casefold()).split())


def load_documents(path):
    docs, seen = [], set()
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                if not isinstance(doc, dict) or not isinstance(doc.get("id"), str) or not doc["id"].strip():
                    raise ValueError("id must be a nonempty string")
                if not isinstance(doc.get("text"), str) or len(doc["text"]) > 1_000_000:
                    raise ValueError("text must be a string of at most 1,000,000 characters")
                if doc["id"] in seen:
                    raise ValueError("duplicate document id")
            except (ValueError, TypeError) as exc:
                raise ValueError(f"line {number}: {exc}") from exc
            seen.add(doc["id"])
            docs.append(doc)
    return sorted(docs, key=lambda doc: doc["id"])


def alias_index(config):
    index = {}
    for label, groups in config.items():
        if label not in {"PER", "ORG", "LOC"}:
            raise ValueError(f"unsupported entity label: {label}")
        for canonical, aliases in groups.items():
            for alias in [canonical, *aliases]:
                key = (label, normalize(alias))
                if not key[1]:
                    raise ValueError("empty alias")
                if key in index and index[key] != canonical:
                    raise ValueError(f"ambiguous alias: {alias}")
                index[key] = canonical
    return index


class BaselineExtractor:
    """Explicit alias dictionary matching; this is not a trained NER model."""
    name = "dictionary-baseline"

    def __init__(self, config):
        alias_index(config)
        self.entries = [(label, alias) for label, groups in config.items()
                        for canonical, aliases in groups.items() for alias in set([canonical, *aliases])]

    def extract(self, text):
        candidates = []
        for label, alias in self.entries:
            for match in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.IGNORECASE):
                candidates.append(dict(label=label, text=match.group(), start=match.start(), end=match.end(), score=1.0))
        chosen = []
        for item in sorted(candidates, key=lambda x: (-(x["end"] - x["start"]), x["start"], x["label"])):
            if not any(item["start"] < old["end"] and old["start"] < item["end"] for old in chosen):
                chosen.append(item)
        return sorted(chosen, key=lambda x: x["start"])


def run(docs, config, extractor, resolver=None):
    aliases = alias_index(config)
    mentions, transactions = [], []
    for doc in docs:
        for item in extractor.extract(doc["text"]):
            if item["label"] not in {"PER", "ORG", "LOC"}:
                continue
            start, end = item["start"], item["end"]
            if not 0 <= start < end <= len(doc["text"]):
                raise ValueError("extractor returned invalid offsets")
            surface = doc["text"][start:end]
            canonical = aliases.get((item["label"], normalize(surface)), normalize(surface))
            mentions.append(dict(id=stable_id(doc["id"], start, end, item["label"]), document_id=doc["id"],
                                 label=item["label"], text=surface, start=start, end=end,
                                 canonical=canonical, key=normalize(canonical), score=float(item["score"])))
        # Deliberately narrow transaction grammar. Co-occurrence never implies payment.
        local = [m for m in mentions if m["document_id"] == doc["id"] and m["label"] == "ORG"]
        for source in local:
            for target in local:
                if doc["text"][source["end"]:target["start"]] != " paid ":
                    continue
                match = re.match(r" USD ([0-9]+(?:\.[0-9]{2})?)(?=[.\s]|$)", doc["text"][target["end"]:])
                if match:
                    transactions.append(dict(id=stable_id(doc["id"], source["start"], target["end"]),
                                             document_id=doc["id"], source_key=source["key"], target_key=target["key"],
                                             amount=match[1], currency="USD", start=source["start"],
                                             end=target["end"] + match.end()))
    entities = resolver(mentions) if resolver else resolve_local(mentions)
    lookup = {(e["label"], e["key"]): e["id"] for e in entities}
    for mention in mentions:
        mention["entity_id"] = lookup[mention["label"], mention["key"]]
    for tx in transactions:
        tx["source_id"] = lookup["ORG", tx.pop("source_key")]
        tx["target_id"] = lookup["ORG", tx.pop("target_key")]
    return dict(schema_version=1, extraction_mode=extractor.name, documents=docs, entities=entities,
                mentions=sorted(mentions, key=lambda m: m["id"]), transactions=sorted(transactions, key=lambda t: t["id"]))


def resolve_local(mentions):
    groups = {}
    for m in mentions:
        groups.setdefault((m["label"], m["key"]), set()).add(m["canonical"])
    return [dict(id=stable_id(label, key), label=label, key=key, name=min(names))
            for (label, key), names in sorted(groups.items())]
