from brownie import reverts
from eth_abi import encode
from utils.evm_script import encode_call_script


MODULE_ID = 3
FACTORY_NAME = "Update module shares factory"
CURRENT_STAKE_SHARE_LIMIT = 9_000
CURRENT_PRIORITY_EXIT_SHARE = 500


def _encode_module_payload(current_stake, new_stake, current_priority, new_priority):
    return encode(["uint16", "uint16", "uint16", "uint16"], [current_stake, new_stake, current_priority, new_priority])


def _deploy_factory(owner, staking_router, UpdateStakingModuleShareLimits):
    return owner.deploy(
        UpdateStakingModuleShareLimits,
        owner,
        FACTORY_NAME,
        staking_router,
        MODULE_ID,
        500,  # +5%
        400,  # -4%
        300,
        200,
    )


def _deploy_router(owner, StakingRouterStub):
    router = owner.deploy(StakingRouterStub)
    router.setModuleShares(MODULE_ID, CURRENT_STAKE_SHARE_LIMIT, CURRENT_PRIORITY_EXIT_SHARE)
    return router


def test_create_evm_script(owner, StakingRouterStub, UpdateStakingModuleShareLimits):
    router = _deploy_router(owner, StakingRouterStub)
    factory = _deploy_factory(owner, router, UpdateStakingModuleShareLimits)
    assert factory.trustedCaller() == owner
    assert factory.name() == FACTORY_NAME
    new_stake = CURRENT_STAKE_SHARE_LIMIT + 200
    new_priority = CURRENT_PRIORITY_EXIT_SHARE - 150
    calldata = _encode_module_payload(
        CURRENT_STAKE_SHARE_LIMIT,
        new_stake,
        CURRENT_PRIORITY_EXIT_SHARE,
        new_priority,
    )

    evm_script = factory.createEVMScript(owner, calldata)

    expected = encode_call_script(
        [
            (
                router.address,
                router.updateModuleShares.encode_input(
                    MODULE_ID,
                    new_stake,
                    new_priority,
                ),
            )
        ]
    )

    assert evm_script == expected


def test_reverts_if_current_values_changed(owner, StakingRouterStub, UpdateStakingModuleShareLimits):
    router = _deploy_router(owner, StakingRouterStub)
    factory = _deploy_factory(owner, router, UpdateStakingModuleShareLimits)

    calldata = _encode_module_payload(
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_STAKE_SHARE_LIMIT + 100,
        CURRENT_PRIORITY_EXIT_SHARE,
        CURRENT_PRIORITY_EXIT_SHARE,
    )

    factory.createEVMScript(owner, calldata)

    router.setModuleShares(MODULE_ID, CURRENT_STAKE_SHARE_LIMIT + 1, CURRENT_PRIORITY_EXIT_SHARE)

    with reverts("CURRENT_VALUES_MISMATCH"):
        factory.createEVMScript(owner, calldata)


def test_reverts_when_stake_delta_exceeds_cap(owner, StakingRouterStub, UpdateStakingModuleShareLimits):
    router = _deploy_router(owner, StakingRouterStub)
    factory = _deploy_factory(owner, router, UpdateStakingModuleShareLimits)

    calldata = _encode_module_payload(
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_STAKE_SHARE_LIMIT + 501,
        CURRENT_PRIORITY_EXIT_SHARE,
        CURRENT_PRIORITY_EXIT_SHARE,
    )

    with reverts("SHARE_LIMITS"):
        factory.createEVMScript(owner, calldata)


def test_reverts_when_priority_delta_exceeds_cap(owner, StakingRouterStub, UpdateStakingModuleShareLimits):
    router = _deploy_router(owner, StakingRouterStub)
    factory = _deploy_factory(owner, router, UpdateStakingModuleShareLimits)

    calldata = _encode_module_payload(
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_PRIORITY_EXIT_SHARE,
        CURRENT_PRIORITY_EXIT_SHARE - 201,
    )

    with reverts("EXIT_THRESHOLD_LIMITS"):
        factory.createEVMScript(owner, calldata)


def test_reverts_when_no_changes(owner, StakingRouterStub, UpdateStakingModuleShareLimits):
    router = _deploy_router(owner, StakingRouterStub)
    factory = _deploy_factory(owner, router, UpdateStakingModuleShareLimits)

    calldata = _encode_module_payload(
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_PRIORITY_EXIT_SHARE,
        CURRENT_PRIORITY_EXIT_SHARE,
    )

    with reverts("NO_CHANGES"):
        factory.createEVMScript(owner, calldata)


def test_decode_call_data(owner, StakingRouterStub, UpdateStakingModuleShareLimits):
    router = _deploy_router(owner, StakingRouterStub)
    factory = _deploy_factory(owner, router, UpdateStakingModuleShareLimits)
    calldata = _encode_module_payload(1, 2, 3, 4)

    decoded = factory.decodeEVMScriptCallData(calldata)

    assert decoded == [1, 2, 3, 4]


def test_only_trusted_caller(owner, stranger, StakingRouterStub, UpdateStakingModuleShareLimits):
    router = _deploy_router(owner, StakingRouterStub)
    factory = _deploy_factory(owner, router, UpdateStakingModuleShareLimits)
    calldata = _encode_module_payload(
        CURRENT_STAKE_SHARE_LIMIT,
        CURRENT_STAKE_SHARE_LIMIT + 100,
        CURRENT_PRIORITY_EXIT_SHARE,
        CURRENT_PRIORITY_EXIT_SHARE + 100,
    )

    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata)
