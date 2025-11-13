import os
import json
from brownie import chain, network

from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    get_network_name,
    prompt_bool,
)
from utils import log

from brownie import AllowedMerkleGatesRegistry


def main():
    network_name = get_network_name()
    deployer = get_deployer_account(get_is_live(), network=network_name)

    admin = os.environ.get("ALLOWED_MERKLE_GATES_ADMIN")
    if not admin:
        raise EnvironmentError("Please set ALLOWED_MERKLE_GATES_ADMIN env variable")

    log.br()
    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.br()
    log.nb("Admin", admin)


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

    registry = AllowedMerkleGatesRegistry.deploy(admin, tx_params)

    log.br()
    log.ok("AllowedMerkleGatesRegistry deployed", registry.address)

    if get_is_live():
        # Save artifacts into deployed-sm-<network>.json
        deployment_artifacts = {
            "AllowedMerkleGatesRegistry": {
                "contract": "AllowedMerkleGatesRegistry",
                "address": registry.address,
                "constructorArgs": [admin],
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

        if get_env("FORCE_VERIFY", False):
            log.ok("Verifying AllowedMerkleGatesRegistry...")
            AllowedMerkleGatesRegistry.publish_source(registry)

    log.br()
    print("Hit <Enter> to quit script")
    input()
