import json
import sys
from typing import Any, Dict

CONFIG = "config.json"


def read_config() -> Dict[str, Any]:
    """
    Read JSON configuration file CONFIG.

    Returns:
        A dictionary containing the addresses of Elasticsearch node,
        index names and field names in case of success.
        Will return an empty dictionary when the file could not be found.
    """
    try:
        with open(CONFIG, "rt") as config:
            conf = json.load(config)
    except (FileNotFoundError, IsADirectoryError):
        print(f"Could not find configuration file {CONFIG}.", file=sys.stderr)
        return {}

    return conf
