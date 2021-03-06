# Query proxy between the data portal of AquaDiva and Elasticsearch
[![Works with Python 3.6+](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-informational.svg)](https://www.python.org/downloads/)[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/AquaDiva-INFRA1/ad-query-proxy/blob/main/LICENSE)[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

The semantic search in the [AquaDiva](https://www.aquadiva.uni-jena.de/) data portal is powered by a domain-specific ontology. This proxy translates ontology IDs into Elasticsearch search terms and queries a specifically prepared index.

To set up the proxy, please follow the instructions in the INSTALL.MD.

Elasticsearch is a trademark of Elasticsearch BV, registered in the U.S. and in other countries.

This work has been funded by the German Research Foundation (DFG) as part of the project D01 in the Collaborative Research Center (CRC) 1076 “AquaDiva”.
