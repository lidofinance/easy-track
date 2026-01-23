import json
import os

from brownie import (
    ReportWithdrawalsForSlashedValidators,  # type: ignore
    chain,
    web3,
)

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
    assert type(network_name) is str

    deployer = get_deployer_account(
        get_is_live(), network=network_name, dev_ldo_transfer=False
    )
    trusted_caller = _get_trusted_caller()
    module_address = _get_module_address()
    factory_name = _get_factory_name()

    log.br()
    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.ok("Chain ID", chain.id)
    log.ok("Deployer", deployer)
    log.br()
    log.ok("Trusted caller", trusted_caller)
    log.ok("Module address", module_address)
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

    constructor_args = (
        trusted_caller,
        factory_name,
        module_address,
    )
    factory = ReportWithdrawalsForSlashedValidators.deploy(
        *constructor_args, {"from": deployer}
    )

    log.br()
    log.ok("Deployed ReportWithdrawalsForSlashedValidators", factory.address)

    if get_is_live():
        # Save artifacts into deployed-sm-<network>.json
        new_entry = {
            "ReportWithdrawalsForSlashedValidators": {
                "contract": "ReportWithdrawalsForSlashedValidators",
                "address": factory.address,
                "constructorArgs": constructor_args,
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
            log.ok("Verifying ReportWithdrawalsForSlashedValidators...")
            ReportWithdrawalsForSlashedValidators.publish_source(factory)

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


def _get_module_address():
    addr = os.environ.get("MODULE_ADDRESS")
    if not web3.is_address(addr):
        raise ValueError(
            f"{addr} is not a valid address, check the MODULE_ADDRESS env variable"
        )
    return addr


def _get_factory_name():
    name = os.environ.get("FACTORY_NAME")
    if not name:
        raise ValueError("Please provide non-empty name via FACTORY_NAME env variable")
    return name
