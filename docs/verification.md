# Verification ledger

Local verification on Python 3.11.9:

- `python -m unittest discover -s tests -p 'test_*.py' -v`: 9 tests passed.
- `python -m entitygraph.cli --output outputs/demo`: 4 documents, 23 mentions, 8 resolved entities, 2 payments; actual JSON and searchable HTML generated.
- `python -m compileall -q entitygraph`: passed.
- Public-bound files scanned for common credential tokens, private keys, personal email addresses and local user paths: no matches. Synthetic emails use `.example`.

Java and Maven are not installed locally. A local packaging probe without build isolation failed because the preinstalled environment lacks `wheel`; normal isolated installation is exercised in CI.

GitHub Actions [run 36650565715](https://github.com/dileepreddy27/entitygraph/actions/runs/36650565715) completed successfully for implementation commit `14a21b10dcfc336fe3ffc9eead90787b61a30fb3`. It verified isolated package installation, the 9 Python tests and offline demo, Spark/local graph parity, two Neo4j imports with exact node counts and mention lineage, 2 Maven/JUnit tests, and live Java HTTP checks (8 entities returned and HTTP 400 for an invalid identifier).

Optional Hugging Face model inference, Docker Compose on this Windows machine, and large-data performance evaluation have not been run. No trained-model accuracy is claimed.
