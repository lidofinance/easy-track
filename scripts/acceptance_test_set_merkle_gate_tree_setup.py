from dataclasses import dataclass

from brownie import chain, SetMerkleGateTree

from utils import log


@dataclass
class DeployConfig:
    trusted_caller: str
    allowed_merkle_gates_registry: str


deploy_config = DeployConfig(
    trusted_caller="",
    allowed_merkle_gates_registry="",
)


deployment_tx_hash = ""


def main():
    tx = chain.get_transaction(deployment_tx_hash)

    log.br()
    log.nb("tx of creation", deployment_tx_hash)

    log.br()
    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("allowed_merkle_gates_registry", deploy_config.allowed_merkle_gates_registry)

    log.br()

    set_merkle_gate_tree_factory = SetMerkleGateTree.at(tx.contract_address)
    log.nb('SetMerkleGateTree address (from tx)', set_merkle_gate_tree_factory)

    log.br()

    assert set_merkle_gate_tree_factory.trustedCaller() == deploy_config.trusted_caller
    log.nb('Trusted caller is correct')

    assert set_merkle_gate_tree_factory.allowedMerkleGatesRegistry() == deploy_config.allowed_merkle_gates_registry
    log.nb('AllowedMerkleGatesRegistry is correct')

    log.br()
