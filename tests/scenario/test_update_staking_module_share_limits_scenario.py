import pytest
from brownie import StakingRouterStub, UpdateStakingModuleShareLimits, reverts

from utils.evm_script import encode_calldata


FACTORY_NAME = "CSM v3"
CURRENT_STAKE_SHARE_LIMIT = 500
CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD = 9000


def create_calldata(current_stake, new_stake, current_priority, new_priority):
    return encode_calldata(
        ["uint16", "uint16", "uint16", "uint16"],
        [current_stake, new_stake, current_priority, new_priority],
    )


@pytest.fixture(scope="module")
def staking_router_contract(owner, use_deployed_contracts_from_env, active_staking_router):
    if use_deployed_contracts_from_env:
        return active_staking_router

    router = owner.deploy(StakingRouterStub)
    router.setStakingModule(3, owner.address, {"from": owner})
    router.setModuleShares(
        3,
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_PRIORITY_EXIT_SHARE_THRESHOLD,
        {"from": owner},
    )
    return router


@pytest.fixture(scope="module")
def module_id(
    staking_router_contract,
    use_deployed_contracts_from_env,
    active_cs_module,
    ensure_module_in_staking_router,
    ensure_module_unpaused,
    ensure_module_operator,
):
    if use_deployed_contracts_from_env:
        module_id = ensure_module_in_staking_router(active_cs_module, "CSM")
        ensure_module_unpaused(active_cs_module)
        ensure_module_operator(active_cs_module)
        return module_id

    return 3


@pytest.fixture(scope="module")
def update_staking_module_share_limits_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    staking_router_contract,
    module_id,
):
    factory = owner.deploy(
        UpdateStakingModuleShareLimits,
        commitee_multisig,
        FACTORY_NAME,
        staking_router_contract.address,
        module_id,
        500,  # max stake share increase
        400,  # max stake share decrease
        300,  # max priority exit threshold increase
        200,  # max priority exit threshold decrease
    )

    permissions = (
        staking_router_contract.address
        + staking_router_contract.updateModuleShares.signature[2:]
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
    staking_router_contract,
    update_staking_module_share_limits_factory,
    module_id,
):
    module_before = staking_router_contract.getStakingModule(module_id)
    current_stake_share_limit = module_before[4]
    current_priority_exit_threshold = module_before[10]
    if current_stake_share_limit <= 9_800:
        new_stake_share_limit = current_stake_share_limit + 200
    else:
        new_stake_share_limit = current_stake_share_limit - 200

    if current_priority_exit_threshold >= 150:
        new_priority_exit_threshold = current_priority_exit_threshold - 150
    else:
        new_priority_exit_threshold = current_priority_exit_threshold + 150

    evm_script_calldata = create_calldata(
        current_stake_share_limit,
        new_stake_share_limit,
        current_priority_exit_threshold,
        new_priority_exit_threshold,
    )

    tx = easytrack_executor(
        commitee_multisig,
        update_staking_module_share_limits_factory,
        evm_script_calldata,
    )

    module_after = staking_router_contract.getStakingModule(module_id)
    assert module_after[4] == new_stake_share_limit
    assert module_after[10] == new_priority_exit_threshold

    assert "ModuleSharesUpdated" in tx.events


def test_update_staking_module_share_limits_reverts_for_missing_module(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    staking_router_contract,
    use_deployed_contracts_from_env,
):
    if use_deployed_contracts_from_env:
        pytest.skip("local stub only")

    missing_module_id = 999
    factory = owner.deploy(
        UpdateStakingModuleShareLimits,
        commitee_multisig,
        FACTORY_NAME + "-MISSING",
        staking_router_contract.address,
        missing_module_id,
        500,
        400,
        300,
        200,
    )

    permissions = (
        staking_router_contract.address
        + staking_router_contract.updateModuleShares.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )

    evm_script_calldata = create_calldata(0, 100, 0, 100)

    with reverts("StakingModuleUnregistered: "):
        et_contracts.easy_track.createMotion(
            factory.address,
            evm_script_calldata,
            {"from": commitee_multisig},
        )
