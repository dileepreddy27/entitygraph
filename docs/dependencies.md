# Dependency and data notes

The offline Python pipeline uses only the standard library. Optional packages are downloaded by the user and are not vendored: Transformers and Tokenizers (Apache-2.0), PyTorch (BSD-style), PySpark (Apache-2.0), and the Neo4j Python driver (Apache-2.0). Java uses Neo4j's driver and Jackson (Apache-2.0) and JUnit (EPL-2.0). Neo4j Community is supplied as its separate GPLv3 Docker image. Consult each resolved dependency's license for authoritative terms and transitive dependencies.

The default optional model identifier is `dslim/bert-base-NER`; model weights are not included. Review its model card, training-data provenance and applicable terms before use. This repository does not train a model or publish a trained checkpoint.

All fixture text and alias names were authored for this demonstration. No external corpus is embedded. No external images, fonts, or client libraries are used by the HTML report.

Version ranges support installation but are not a complete reproducible lockfile. CI records the actual environment in its installation logs; pin resolved versions and the model commit before a controlled evaluation.
