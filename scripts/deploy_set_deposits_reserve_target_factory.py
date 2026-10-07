import json
import os

from brownie import SetDepositsReserveTarget, chain, web3

from utils import lido, log
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

    is_live = get_is_live()
    deployer = get_deployer_account(is_live, network=network_name, dev_ldo_transfer=False)
    trusted_caller = _get_trusted_caller()
    max_deposits_reserve_target = _get_max_deposits_reserve_target()
    lido_address = lido.addresses(network=network_name).steth

    log.br()
    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.ok("Chain ID", chain.id)
    log.ok("Deployer", deployer)
    log.br()
    log.ok("Trusted caller", trusted_caller)
    log.ok("Maximum deposits reserve target", max_deposits_reserve_target)
    log.ok("Lido address", lido_address)

    log.br()
    print("Proceed? [yes/no]: ")
    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if is_live:
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "50 gwei"

    constructor_args = (
        trusted_caller,
        max_deposits_reserve_target,
        lido_address,
    )
    factory = SetDepositsReserveTarget.deploy(*constructor_args, tx_params)

    log.br()
    log.ok("Deployed SetDepositsReserveTarget", factory.address)

    if is_live:
        entry_key = "SetDepositsReserveTarget"
        new_entry = {
            entry_key: {
                "contract": "SetDepositsReserveTarget",
                "address": factory.address,
                "constructorArgs": constructor_args,
                "txHash": factory.tx.txid,
            }
        }

        artifacts_path = f"deployed-{network_name}.json"
        try:
            with open(artifacts_path, "r") as previous_artifacts_file:
                artifacts = json.load(previous_artifacts_file)
        except FileNotFoundError:
            artifacts = {}

        artifacts.update(new_entry)

        with open(artifacts_path, "w") as artifacts_file:
            json.dump(artifacts, artifacts_file, indent=4)

        log.nb("Artifacts saved to", artifacts_path)

        if get_env("FORCE_VERIFY", False):
            log.ok("Verifying SetDepositsReserveTarget...")
            SetDepositsReserveTarget.publish_source(factory)

    log.br()
    print("Hit <Enter> to quit script")
    input()


def _get_trusted_caller():
    trusted_caller = os.environ.get("TRUSTED_CALLER")
    if not web3.is_address(trusted_caller):
        raise ValueError(f"{trusted_caller} is not a valid address, check the TRUSTED_CALLER env variable")
    return trusted_caller


def _get_max_deposits_reserve_target():
    raw_value = os.environ.get("MAX_DEPOSITS_RESERVE_TARGET", "").strip()
    if not raw_value:
        raise ValueError("Please provide MAX_DEPOSITS_RESERVE_TARGET in wei via its env variable")

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError("MAX_DEPOSITS_RESERVE_TARGET must be an integer") from exc

    if value < 0 or value >= 2**256:
        raise ValueError("MAX_DEPOSITS_RESERVE_TARGET must fit into uint256")
    return value
