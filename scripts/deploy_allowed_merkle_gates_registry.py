import os
import json
from brownie import chain, network, web3

from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    get_network_name,
    prompt_bool,
)
from utils import log

from brownie import AllowedMerkleGatesRegistry


def _get_admin():
    admin = os.environ.get("ALLOWED_MERKLE_GATES_ADMIN")
    if not admin:
        raise EnvironmentError("Please set ALLOWED_MERKLE_GATES_ADMIN env variable")
    return admin


def _get_registry_name():
    name = os.environ.get("ALLOWED_MERKLE_GATES_REGISTRY_NAME")
    if not name:
        raise EnvironmentError("Please set ALLOWED_MERKLE_GATES_REGISTRY_NAME env variable")
    return name


def _get_initial_gates_and_titles():
    gates_raw = os.environ.get("ALLOWED_MERKLE_GATES_ADDRESSES", "").strip()
    titles_raw = os.environ.get("ALLOWED_MERKLE_GATES_TITLES", "").strip()
    if not gates_raw and not titles_raw:
        return [], []
    if not gates_raw or not titles_raw:
        raise EnvironmentError(
            "Please set both ALLOWED_MERKLE_GATES_ADDRESSES and ALLOWED_MERKLE_GATES_TITLES env variables"
        )

    gates = [item.strip() for item in gates_raw.split(",") if item.strip()]
    titles = [item.strip() for item in titles_raw.split(",") if item.strip()]

    if not gates and not titles:
        return [], []
    if len(gates) != len(titles):
        raise ValueError(
            "ALLOWED_MERKLE_GATES_ADDRESSES and ALLOWED_MERKLE_GATES_TITLES length mismatch"
        )

    for gate in gates:
        if not web3.is_address(gate):
            raise ValueError(f"{gate} is not a valid address in ALLOWED_MERKLE_GATES_ADDRESSES")
    for title in titles:
        if not isinstance(title, str):
            raise ValueError(f"{title} is not a valid title in ALLOWED_MERKLE_GATES_TITLES")

    return gates, titles


def main():
    network_name = get_network_name()
    deployer = get_deployer_account(get_is_live(), network=network_name)
    admin = _get_admin()
    registry_name = _get_registry_name()
    initial_gates, initial_titles = _get_initial_gates_and_titles()

    log.br()
    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.br()
    log.nb("Admin", admin)
    log.nb("Registry name", registry_name)
    log.nb("Initial gates", len(initial_gates))


    log.br()
    print("Proceed? [yes/no]: ")
    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        # project-wide gas defaults
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "50 gwei"

    registry = AllowedMerkleGatesRegistry.deploy(
        admin,
        registry_name,
        initial_gates,
        initial_titles,
        tx_params,
    )

    log.br()
    log.ok("AllowedMerkleGatesRegistry deployed", registry.address)

    if get_is_live():
        # Save artifacts into deployed-sm-<network>.json
        entry_key = f"AllowedMerkleGatesRegistry:{registry_name}"
        deployment_artifacts = {
            entry_key: {
                "contract": "AllowedMerkleGatesRegistry",
                "address": registry.address,
                "constructorArgs": [admin, registry_name, initial_gates, initial_titles],
                "name": registry_name,
            }
        }

        artifacts_path = f"deployed-sm-{network_name}.json"
        if os.path.exists(artifacts_path):
            try:
                with open(artifacts_path, "r") as prev:
                    existing = json.load(prev)
            except Exception:
                existing = {}
            existing.update(deployment_artifacts)
            deployment_artifacts = existing

        with open(artifacts_path, "w") as out:
            json.dump(deployment_artifacts, out, indent=4)

        log.ok("Saved artifact key", entry_key)

        if get_env("FORCE_VERIFY", False):
            log.ok("Verifying AllowedMerkleGatesRegistry...")
            AllowedMerkleGatesRegistry.publish_source(registry)

    log.br()
    print("Hit <Enter> to quit script")
    input()
