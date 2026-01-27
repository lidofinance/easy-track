from dataclasses import dataclass

from brownie import chain, SettleGeneralDelayedPenalty

from utils import log


@dataclass
class DeployConfig:
    trusted_caller: str
    factory_name: str
    module_address: str


deploy_config = DeployConfig(
    trusted_caller="",
    factory_name="",
    module_address=""
)


deployment_tx_hash = ""


def main():

    tx = chain.get_transaction(deployment_tx_hash)

    log.br()

    log.nb("tx of creation", deployment_tx_hash)

    log.br()

    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("factory_name", deploy_config.factory_name)
    log.nb("module_address", deploy_config.module_address)

    log.br()

    settle_general_delayed_penalty_factory = SettleGeneralDelayedPenalty.at(tx.contract_address)
    log.nb('SettleGeneralDelayedPenalty address (from tx)', settle_general_delayed_penalty_factory)

    log.br()

    assert settle_general_delayed_penalty_factory.module() == deploy_config.module_address
    log.nb('Module address is correct')

    assert settle_general_delayed_penalty_factory.trustedCaller() == deploy_config.trusted_caller
    log.nb('Trusted caller is correct')

    log.br()
