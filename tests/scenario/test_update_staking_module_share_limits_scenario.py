import pytest
from brownie import StakingRouterStub, UpdateStakingModuleShareLimits

from utils.evm_script import encode_calldata


FACTORY_NAME = "SR"
MODULE_ID = 3
CURRENT_STAKE_SHARE_LIMIT = 9000
CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD = 500


def create_calldata(current_stake, new_stake, current_priority, new_priority):
    return encode_calldata(
        ["uint16", "uint16", "uint16", "uint16"],
        [current_stake, new_stake, current_priority, new_priority],
    )


@pytest.fixture(scope="module")
def staking_router_stub(owner):
    router = owner.deploy(StakingRouterStub)
    router.setModuleShares(
        MODULE_ID,
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
        {"from": owner},
    )
    return router


@pytest.fixture(scope="module")
def update_staking_module_share_limits_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    staking_router_stub,
):
    factory = owner.deploy(
        UpdateStakingModuleShareLimits,
        commitee_multisig,
        FACTORY_NAME,
        staking_router_stub.address,
        MODULE_ID,
        500,  # max stake share increase
        400,  # max stake share decrease
        300,  # max priority exit threshold increase
        200,  # max priority exit threshold decrease
    )

    permissions = (
        staking_router_stub.address
        + staking_router_stub.updateModuleShares.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


def test_update_staking_module_share_limits_via_motion_scenario(
    commitee_multisig,
    easytrack_executor,
    staking_router_stub,
    update_staking_module_share_limits_factory,
):
    new_stake_share_limit = CURRENT_STAKE_SHARE_LIMIT + 200
    new_priority_exit_threshold = CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD - 150

    module_before = staking_router_stub.getStakingModule(MODULE_ID)
    assert module_before[4] == CURRENT_STAKE_SHARE_LIMIT
    assert module_before[10] == CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD

    evm_script_calldata = create_calldata(
        CURRENT_STAKE_SHARE_LIMIT,
        new_stake_share_limit,
        CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
        new_priority_exit_threshold,
    )

    tx = easytrack_executor(
        commitee_multisig,
        update_staking_module_share_limits_factory,
        evm_script_calldata,
    )

    module_after = staking_router_stub.getStakingModule(MODULE_ID)
    assert module_after[4] == new_stake_share_limit
    assert module_after[10] == new_priority_exit_threshold

    assert "ModuleSharesUpdated" in tx.events
