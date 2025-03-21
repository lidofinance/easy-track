import json
import os

from brownie import (
    chain,
    network,
    AddMEVBoostRelays,
    RemoveMEVBoostRelays,
    EditMEVBoostRelays,
    web3,
)

from utils import lido, log, deployment
from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)


def get_trusted_caller():
    if "TRUSTED_CALLER" not in os.environ:
        raise EnvironmentError("Please set TRUSTED_CALLER env variable")
    trusted_caller = os.environ["TRUSTED_CALLER"]

    assert web3.isAddress(trusted_caller), "Trusted caller address is not valid"

    return trusted_caller


def main():
    network_name = get_network_name()

    addresses = lido.addresses(network=network_name)
    deployer = get_deployer_account(get_is_live(), network=network_name)
    trusted_caller = get_trusted_caller()

    evm_script_executor = addresses.evm_script_executor
    mev_boost_allow_list = addresses.mev_boost_list

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.br()

    log.nb("Deployed MEV Boost Relay Allowed List", mev_boost_allow_list)
    log.nb("Deployed EVMScript Executor", evm_script_executor)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "300 gwei"

    deploy_rmc_factories(
        network_name,
        trusted_caller,
        mev_boost_allow_list,
        tx_params,
    )


def deploy_rmc_factories(
    network_name,
    trusted_caller,
    mev_boost_allow_list,
    tx_params,
):
    deployment_artifacts = {}

    # AddMEVBoostRelays
    add_mev_boost_relay = AddMEVBoostRelays.deploy(
        trusted_caller,
        mev_boost_allow_list,
        tx_params,
    )
    deployment_artifacts["AddMEVBoostRelays"] = {
        "contract": "AddMEVBoostRelays",
        "address": add_mev_boost_relay.address,
        "constructorArgs": [trusted_caller, mev_boost_allow_list],
    }

    log.ok("Deployed AddMEVBoostRelays", add_mev_boost_relay.address)

    # RemoveMEVBoostRelays
    remove_mev_boost_relay = RemoveMEVBoostRelays.deploy(
        trusted_caller,
        mev_boost_allow_list,
        tx_params,
    )
    deployment_artifacts["RemoveMEVBoostRelays"] = {
        "contract": "RemoveMEVBoostRelays",
        "address": remove_mev_boost_relay.address,
        "constructorArgs": [trusted_caller, mev_boost_allow_list],
    }

    log.ok("Deployed RemoveMEVBoostRelays", remove_mev_boost_relay.address)

    # EditMEVBoostRelays
    edit_mev_boost_relay = EditMEVBoostRelays.deploy(
        trusted_caller,
        mev_boost_allow_list,
        tx_params,
    )
    deployment_artifacts["EditMEVBoostRelays"] = {
        "contract": "EditMEVBoostRelays",
        "address": edit_mev_boost_relay.address,
        "constructorArgs": [trusted_caller, mev_boost_allow_list],
    }

    log.ok("Deployed EditMEVBoostRelays", edit_mev_boost_relay.address)

    filename = f"et-rmc-deployed-{network_name}.json"

    log.br()
    log.ok(f"All MEV Boost Relay factories have been deployed. Publishing...")

    log.br()
    log.ok("All MEV Boost Relay factories have been verified and published. Saving artifacts...")

    with open(filename, "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.br()
    log.ok("Deployment artifacts have been saved to", filename)

    AddMEVBoostRelays.publish_source(add_mev_boost_relay)
    RemoveMEVBoostRelays.publish_source(remove_mev_boost_relay)
    EditMEVBoostRelays.publish_source(edit_mev_boost_relay)
