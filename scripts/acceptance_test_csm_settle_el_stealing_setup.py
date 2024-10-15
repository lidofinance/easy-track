from dataclasses import dataclass

from brownie import chain, CSMSettleElStealingPenalty

from utils import log


@dataclass
class DeployConfig:
    trusted_caller: str
    csm_address: str


deploy_config = DeployConfig(
    trusted_caller="",
    csm_address=""
)


deployment_tx_hash = ""


def main():

    tx = chain.get_transaction(deployment_tx_hash)

    log.br()

    log.nb("tx of creation", deployment_tx_hash)

    log.br()

    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("csm_address", deploy_config.csm_address)

    log.br()

    settle_el_stealing_factory = CSMSettleElStealingPenalty.at(tx.contract_address)
    log.nb('CSMSettleElStealingPenalty address (from tx)', settle_el_stealing_factory)

    log.br()

    assert settle_el_stealing_factory.csm() == deploy_config.csm_address
    log.nb('CSM address is correct')

    assert settle_el_stealing_factory.trustedCaller() == deploy_config.trusted_caller
    log.nb('Trusted caller is correct')

    log.br()
