import json
import os

from brownie import (
    chain,
    CSMSettleElStealingPenalty,
    web3,
)

from utils import csm, log
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

    assert web3.is_address(trusted_caller), "Trusted caller address is not valid"

    return trusted_caller


def main():
    network_name = get_network_name()
    csm_contracts = csm.contracts(network=network_name)

    deployer = get_deployer_account(get_is_live(), network=network_name)
    trusted_caller = get_trusted_caller()
    cs_module = csm_contracts.module

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("CSModule module address", cs_module)
    log.ok("Trusted caller", trusted_caller)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return


    log.br()

    deployment_artifacts = {}

    # CSMSettleElStealingPenalty
    csm_settle_el_stealing_penalty = CSMSettleElStealingPenalty.deploy(
        trusted_caller, cs_module.address, {"from": deployer}
    )
    deployment_artifacts["CSMSettleElStealingPenalty"] = {
        "contract": "CSMSettleElStealingPenalty",
        "address": csm_settle_el_stealing_penalty.address,
        "constructorArgs": [trusted_caller, cs_module.address],
    }

    log.ok("Deployed CSMSettleElStealingPenalty", csm_settle_el_stealing_penalty.address)

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving atrifacts...")

    with open(f"deployed-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.nb("Starting code verification.")
    log.br()

    CSMSettleElStealingPenalty.publish_source(csm_settle_el_stealing_penalty)

    log.br()
