import json
import os
from functools import lru_cache

import yaml
import brownie
from utils import log
from utils.config import get_network_name

_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')


@lru_cache(maxsize=1)
def load_addresses():
    """Load all addresses from integration-test-addresses-{network}.yaml.

    Returns an empty dict if the file doesn't exist, letting callers fall back
    to local deployments on networks without a pre-populated addresses file.
    """
    network_name = get_network_name()
    addresses_file = os.path.join(_PROJECT_ROOT, f'integration-test-addresses-{network_name}.yaml')
    try:
        with open(addresses_file) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Invalid YAML in addresses file: {addresses_file}"
        ) from exc


@lru_cache(maxsize=1)
def load_deployed_artifact():
    """Load deployed-{network}.json and return a flat {ContractName: address} map.

    Returns an empty dict if the file doesn't exist.
    """
    network_name = get_network_name()
    file_path = os.path.join(_PROJECT_ROOT, f"deployed-{network_name}.json")
    try:
        with open(file_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}

    return {
        name: entry["address"]
        for name, entry in data.items()
        if isinstance(entry, dict) and "address" in entry
    }


def get_easytrack_address():
    """Get the EasyTrack contract address."""
    return load_addresses().get("easytrack", "")


def get_single_token_config():
    """Get single-token suite config: factory, builder, and instances.

    Falls back to a single synthetic instance when none are configured, so
    parametrized tests still run (deploying everything fresh) on networks
    without an integration-test-addresses file.
    """
    data = load_addresses()
    config = data.get("single_token", {})
    easytrack = data.get("easytrack", "")
    instances = config.get("instances") or [{"name": "default"}]
    return {
        "easytrack": easytrack,
        "factory": config.get("factory", ""),
        "builder": config.get("builder", ""),
        "instances": instances,
    }


def get_multi_token_config():
    """Get multi-token suite config: factory, builder, tokens_registry, and instances.

    Falls back to a single synthetic instance when none are configured, so
    parametrized tests still run (deploying everything fresh) on networks
    without an integration-test-addresses file.
    """
    data = load_addresses()
    config = data.get("multi_token", {})
    easytrack = data.get("easytrack", "")
    instances = config.get("instances") or [{"name": "default"}]
    return {
        "easytrack": easytrack,
        "factory": config.get("factory", ""),
        "builder": config.get("builder", ""),
        "tokens_registry": config.get("tokens_registry", ""),
        "instances": instances,
    }


def try_load_deployed_contract(contract_name, deployed_contracts):
    """Try to load a deployed contract by name from the addresses map.

    Returns the loaded contract instance, or None if no valid address is configured.
    """
    Contract = getattr(brownie, contract_name, None)
    if Contract is None:
        raise ValueError(f"Contract '{contract_name}' not found in brownie")

    address = deployed_contracts.get(contract_name, "")
    if address and address != "local":
        loaded_contract = Contract.at(address)
        log.ok(f"Loaded contract: {contract_name}('{loaded_contract.address}')")
        return loaded_contract

    return None
