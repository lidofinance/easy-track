import os
import json

from brownie import chain
from brownie import SetMerkleGateTree

from utils import log
from utils.config import (
    get_env,
    get_is_live,
    get_network_name,
    get_deployer_account,
    prompt_bool,
)


def _get_trusted_caller():
    addr = os.environ.get("TRUSTED_CALLER")
    if not addr:
        raise EnvironmentError("Please set TRUSTED_CALLER env variable")
    return addr


def _get_factory_name():
    name = os.environ.get("FACTORY_NAME")
    if not name:
        raise EnvironmentError("Please set FACTORY_NAME env variable")
    return name


def main():
    network_name = get_network_name()
    deployer = get_deployer_account(get_is_live(), network=network_name, dev_ldo_transfer=False)
    trusted_caller = _get_trusted_caller()
    factory_name = _get_factory_name()

    log.br()
    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.br()
    log.ok("Trusted caller", trusted_caller)
    log.ok("Factory name", factory_name)

    log.br()
    print("Proceed? [yes/no]: ")
    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "50 gwei"

    factory = SetMerkleGateTree.deploy(
        trusted_caller,
        factory_name,
        tx_params,
    )

    log.br()
    log.ok("Deployed SetMerkleGateTree", factory.address)

    if get_is_live():
        # Save artifacts into deployed-sm-<network>.json
        entry_key = f"SetMerkleGateTree:{factory_name}"
        deployment_artifacts = {
            entry_key: {
                "contract": "SetMerkleGateTree",
                "address": factory.address,
                "constructorArgs": [trusted_caller, factory_name],
                "txHash": factory.tx.txid,
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
            log.ok("Verifying SetMerkleGateTree...")
            SetMerkleGateTree.publish_source(factory)

    log.br()
    print("Hit <Enter> to quit script")
    input()
