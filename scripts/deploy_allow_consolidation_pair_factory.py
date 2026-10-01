import json
import os

from brownie import AllowConsolidationPair, chain, web3

from utils import log
from utils.config import (
    get_deployer_account,
    get_env,
    get_is_live,
    get_network_name,
    prompt_bool,
)


def main():
    network_name = get_network_name()
    assert isinstance(network_name, str)

    deployer = get_deployer_account(
        get_is_live(), network=network_name, dev_ldo_transfer=False
    )
    consolidation_migrator_address = _get_consolidation_migrator_address()

    log.br()
    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.ok("Chain ID", chain.id)
    log.ok("Deployer", deployer)
    log.br()
    log.ok("ConsolidationMigrator address", consolidation_migrator_address)

    log.br()
    print("Proceed? [yes/no]: ")
    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "50 gwei"

    constructor_args = (consolidation_migrator_address,)
    factory = AllowConsolidationPair.deploy(*constructor_args, tx_params)

    log.br()
    log.ok("Deployed AllowConsolidationPair", factory.address)

    if get_is_live():
        entry_key = "AllowConsolidationPair"
        new_entry = {
            entry_key: {
                "contract": "AllowConsolidationPair",
                "address": factory.address,
                "constructorArgs": constructor_args,
                "txHash": factory.tx.txid,
            }
        }

        artifacts_path = f"deployed-sr-{network_name}.json"
        try:
            with open(artifacts_path, "r") as prev:
                artifacts = json.load(prev)
        except FileNotFoundError:
            artifacts = {}

        artifacts.update(new_entry)

        with open(artifacts_path, "w") as out:
            json.dump(artifacts, out, indent=4)

        if get_env("FORCE_VERIFY", False):
            log.ok("Verifying AllowConsolidationPair...")
            AllowConsolidationPair.publish_source(factory)

    log.br()
    print("Hit <Enter> to quit script")
    input()


def _get_consolidation_migrator_address():
    addr = os.environ.get("CONSOLIDATION_MIGRATOR_ADDRESS")
    if not web3.is_address(addr):
        raise ValueError(
            f"{addr} is not a valid address, check the CONSOLIDATION_MIGRATOR_ADDRESS env variable"
        )
    return addr
