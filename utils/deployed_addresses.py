import json
import os
from functools import lru_cache

_ADDRESSES_FILE = os.path.join(os.path.dirname(__file__), '..', 'integration-test-addresses.json')


@lru_cache(maxsize=1)
def load_addresses():
    """Load all addresses from integration-test-addresses.json."""
    try:
        with open(_ADDRESSES_FILE) as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Addresses file not found: {_ADDRESSES_FILE}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in addresses file: {_ADDRESSES_FILE}"
        ) from exc


def get_easytrack_address():
    """Get the EasyTrack contract address."""
    return load_addresses().get("easytrack", "")


def get_single_token_config():
    """Get single-token suite config: factory, builder, and instances."""
    data = load_addresses()
    config = data.get("single_token", {})
    easytrack = data.get("easytrack", "")
    return {
        "easytrack": easytrack,
        "factory": config.get("factory", ""),
        "builder": config.get("builder", ""),
        "instances": config.get("instances", []),
    }


def get_multi_token_config():
    """Get multi-token suite config: factory, builder, tokens_registry, and instances."""
    data = load_addresses()
    config = data.get("multi_token", {})
    easytrack = data.get("easytrack", "")
    return {
        "easytrack": easytrack,
        "factory": config.get("factory", ""),
        "builder": config.get("builder", ""),
        "tokens_registry": config.get("tokens_registry", ""),
        "instances": config.get("instances", []),
    }
