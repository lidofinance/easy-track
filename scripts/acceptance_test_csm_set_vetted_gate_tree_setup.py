from dataclasses import dataclass

from brownie import chain, CSMSetVettedGateTree

from utils import log


@dataclass
class DeployConfig:
    trusted_caller: str
    factory_name: str
    vetted_gate_address: str


deploy_config = DeployConfig(
    trusted_caller="",
    factory_name="",
    vetted_gate_address=""
)


deployment_tx_hash = ""


def main():

    tx = chain.get_transaction(deployment_tx_hash)

    log.br()

    log.nb("tx of creation", deployment_tx_hash)

    log.br()

    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("factory_name", deploy_config.factory_name)
    log.nb("vetted_gate_address", deploy_config.vetted_gate_address)

    log.br()

    set_vetted_gate_tree_factory = CSMSetVettedGateTree.at(tx.contract_address)
    log.nb('CSMSetVettedGateTree address (from tx)', set_vetted_gate_tree_factory)

    log.br()

    assert set_vetted_gate_tree_factory.vettedGate() == deploy_config.vetted_gate_address
    log.nb('VettedGate address is correct')

    assert set_vetted_gate_tree_factory.trustedCaller() == deploy_config.trusted_caller
    log.nb('Trusted caller is correct')

    assert set_vetted_gate_tree_factory.name() == deploy_config.factory_name
    log.nb('Factory name is correct')

    log.br()
