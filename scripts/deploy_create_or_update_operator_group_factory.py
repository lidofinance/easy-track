import json
import os

from brownie import CreateOrUpdateOperatorGroup, chain, web3

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
    trusted_caller = _get_trusted_caller()
    meta_registry_address = _get_meta_registry_address()
    factory_name = _get_factory_name()
    allowed_ext_module_id = _get_allowed_ext_module_id()

    log.br()
    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.ok("Chain ID", chain.id)
    log.ok("Deployer", deployer)
    log.br()
    log.ok("Trusted caller", trusted_caller)
    log.ok("MetaRegistry address", meta_registry_address)
    log.ok("Factory name", factory_name)
    log.ok("Allowed ext module ID", allowed_ext_module_id)

    log.br()
    print("Proceed? [yes/no]: ")
    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer}
    if get_is_live():
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "50 gwei"

    constructor_args = (
        trusted_caller,
        factory_name,
        meta_registry_address,
        allowed_ext_module_id,
    )
    factory = CreateOrUpdateOperatorGroup.deploy(*constructor_args, tx_params)

    log.br()
    log.ok("Deployed CreateOrUpdateOperatorGroup", factory.address)

    if get_is_live():
        entry_key = f"CreateOrUpdateOperatorGroup:{factory_name}"
        new_entry = {
            entry_key: {
                "contract": "CreateOrUpdateOperatorGroup",
                "address": factory.address,
                "constructorArgs": constructor_args,
                "txHash": factory.tx.txid,
            }
        }

        artifacts_path = f"deployed-sm-{network_name}.json"
        try:
            with open(artifacts_path, "r") as prev:
                artifacts = json.load(prev)
        except FileNotFoundError:
            artifacts = {}

        artifacts.update(new_entry)

        with open(artifacts_path, "w") as out:
            json.dump(artifacts, out, indent=4)

        if get_env("FORCE_VERIFY", False):
            log.ok("Verifying CreateOrUpdateOperatorGroup...")
            CreateOrUpdateOperatorGroup.publish_source(factory)

    log.br()
    print("Hit <Enter> to quit script")
    input()


def _get_trusted_caller():
    addr = os.environ.get("TRUSTED_CALLER")
    if not web3.is_address(addr):
        raise ValueError(
            f"{addr} is not a valid address, check the TRUSTED_CALLER env variable"
        )
    return addr


def _get_meta_registry_address():
    addr = os.environ.get("META_REGISTRY_ADDRESS")
    if not web3.is_address(addr):
        raise ValueError(
            f"{addr} is not a valid address, check the META_REGISTRY_ADDRESS env variable"
        )
    return addr


def _get_factory_name():
    name = os.environ.get("FACTORY_NAME")
    if not name:
        raise ValueError("Please provide non-empty name via FACTORY_NAME env variable")
    return name


def _get_allowed_ext_module_id():
    raw = os.environ.get("ALLOWED_EXT_MODULE_ID", "").strip()
    if not raw:
        raise ValueError(
            "Please provide NOR module ID via ALLOWED_EXT_MODULE_ID env variable"
        )
    return int(raw)
