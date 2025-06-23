import pytest
from brownie import SDVTSubmitExitRequestHashes, ZERO_ADDRESS


@pytest.fixture(scope="module")
def sdvt_contract(owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle):
    return SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle, {"from": owner}
    )


def test_deploy(owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, staking_router_stub, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.trustedCaller() == owner
    assert contract.stakingRouter() == staking_router_stub
    assert contract.validatorsExitBusOracle() == validator_exit_bus_oracle
    assert contract.nodeOperatorsRegistry() == sdvt_registry_stub


def test_deploy_zero_staking_router(owner, sdvt_registry_stub, validator_exit_bus_oracle):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, ZERO_ADDRESS, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.stakingRouter() == ZERO_ADDRESS


def test_deploy_zero_validator_exit_bus_oracle(owner, sdvt_registry_stub, staking_router_stub):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, sdvt_registry_stub, staking_router_stub, ZERO_ADDRESS, {"from": owner}
    )
    assert contract.validatorsExitBusOracle() == ZERO_ADDRESS


def test_deploy_zero_node_operators_registry(owner, staking_router_stub, validator_exit_bus_oracle):
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, ZERO_ADDRESS, staking_router_stub, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.nodeOperatorsRegistry() == ZERO_ADDRESS
