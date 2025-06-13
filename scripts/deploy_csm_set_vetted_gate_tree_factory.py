import json
import os

from brownie import (
    chain,
    web3,
    accounts,
    CSMSetVettedGateTree
)

from utils import log
from utils.config import (
    get_env,
    get_is_live,
    get_network_name,
    get_deployer_account,
    prompt_bool,
)

def check_etherscan_token():
    if "ETHERSCAN_TOKEN" not in os.environ:
        raise EnvironmentError("Please set ETHERSCAN_TOKEN env variable")
    etherscan_token = os.environ["ETHERSCAN_TOKEN"]

    assert etherscan_token, "Etherscan API token is not valid"

    return etherscan_token


def get_trusted_caller():
    if "TRUSTED_CALLER" not in os.environ:
        raise EnvironmentError("Please set TRUSTED_CALLER env variable")
    trusted_caller = os.environ["TRUSTED_CALLER"]

    assert web3.is_address(trusted_caller), "Trusted caller address is not valid"

    return trusted_caller


def get_factory_name():
    if "FACTORY_NAME" not in os.environ:
        raise EnvironmentError("Please set FACTORY_NAME env variable")

    factory_name = os.environ["FACTORY_NAME"]

    if not factory_name:
        raise ValueError("Factory name cannot be empty")
    if not isinstance(factory_name, str):
        raise TypeError("Factory name must be a string")
    if len(factory_name) > 32:
        raise ValueError("Factory name must be less than 32 characters")

    return factory_name


def get_vetted_gate_address():
    if "VETTED_GATE_ADDRESS" not in os.environ:
        raise EnvironmentError("Please set VETTED_GATE_ADDRESS env variable")
    vetted_gate_address = os.environ["VETTED_GATE_ADDRESS"]

    assert web3.is_address(vetted_gate_address), "VettedGate address is not valid"

    return vetted_gate_address


def main():
    if get_is_live() and get_env("FORCE_VERIFY", False):
        check_etherscan_token()

    network_name = get_network_name()

    deployer = get_deployer_account(get_is_live(), network=network_name, dev_ldo_transfer=False)
    trusted_caller = get_trusted_caller()
    factory_name = get_factory_name()
    vetted_gate_address = get_vetted_gate_address()

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("chain id", chain.id)

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("VettedGate address", vetted_gate_address)
    log.ok("Trusted caller", trusted_caller)
    log.ok("Factory name", factory_name)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    log.br()

    deployment_artifacts = {}
    
    # Gas parameters following project conventions
    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}
    
    log.nb("Deploying CSMSetVettedGateTree...")
    
    csm_set_vetted_gate_tree = CSMSetVettedGateTree.deploy(
        trusted_caller, 
        factory_name, 
        vetted_gate_address, 
        tx_params
    )
    deployment_artifacts["CSMSetVettedGateTree"] = {
        "contract": "CSMSetVettedGateTree",
        "address": csm_set_vetted_gate_tree.address,
        "constructorArgs": [trusted_caller, factory_name, vetted_gate_address],
    }

    log.ok("Deployed CSMSetVettedGateTree", csm_set_vetted_gate_tree.address)

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving artifacts...")

    with open(f"deployed-csm-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    if get_is_live() and get_env("FORCE_VERIFY", False):
        log.nb("Starting code verification.")
        log.br()

        CSMSetVettedGateTree.publish_source(csm_set_vetted_gate_tree)

    log.br()
