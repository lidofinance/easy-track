from dataclasses import dataclass

from brownie import chain, CreateOrUpdateOperatorGroup

from utils import log


@dataclass
class DeployConfig:
    trusted_caller: str
    factory_name: str
    meta_registry: str


deploy_config = DeployConfig(
    trusted_caller="",
    factory_name="",
    meta_registry="",
)


deployment_tx_hash = ""


def main():
    tx = chain.get_transaction(deployment_tx_hash)

    log.br()
    log.nb("tx of creation", deployment_tx_hash)

    log.br()
    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("factory_name", deploy_config.factory_name)
    log.nb("meta_registry", deploy_config.meta_registry)

    log.br()
    factory = CreateOrUpdateOperatorGroup.at(tx.contract_address)
    log.nb("CreateOrUpdateOperatorGroup address (from tx)", factory)

    log.br()

    assert factory.trustedCaller() == deploy_config.trusted_caller
    log.nb("Trusted caller is correct")

    assert factory.name() == deploy_config.factory_name
    log.nb("Factory name is correct")

    assert factory.metaRegistry() == deploy_config.meta_registry
    log.nb("MetaRegistry address is correct")

    log.br()
