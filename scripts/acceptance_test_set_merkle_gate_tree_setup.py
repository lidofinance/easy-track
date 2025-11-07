from dataclasses import dataclass

from brownie import chain, SetMerkleGateTree

from utils import log


@dataclass
class DeployConfig:
    trusted_caller: str
    factory_name: str
    merkle_gate_address: str


deploy_config = DeployConfig(
    trusted_caller="",
    factory_name="",
    merkle_gate_address=""
)


deployment_tx_hash = ""


def main():

    tx = chain.get_transaction(deployment_tx_hash)

    log.br()

    log.nb("tx of creation", deployment_tx_hash)

    log.br()

    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("factory_name", deploy_config.factory_name)
    log.nb("merkle_gate_address", deploy_config.merkle_gate_address)

    log.br()

    set_merkle_gate_tree_factory = SetMerkleGateTree.at(tx.contract_address)
    log.nb('SetMerkleGateTree address (from tx)', set_merkle_gate_tree_factory)

    log.br()

    assert set_merkle_gate_tree_factory.merkleGate() == deploy_config.merkle_gate_address
    log.nb('MerkleGate address is correct')

    assert set_merkle_gate_tree_factory.trustedCaller() == deploy_config.trusted_caller
    log.nb('Trusted caller is correct')

    assert set_merkle_gate_tree_factory.name() == deploy_config.factory_name
    log.nb('Factory name is correct')

    log.br()
