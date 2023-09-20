import pytest
from brownie import (
    AddNodeOperators,
    chain,
    ActivateNodeOperators,
    DeactivateNodeOperators,
    SetNodeOperatorNames,
    SetNodeOperatorRewardAddresses,
    IncreaseVettedValidatorsLimit,
    IncreaseNodeOperatorsStakingLimitByCommitee,
    UpdateTargetValidatorsLimits,
    TransferNodeOperatorManager,
    RenounceManageSigningKeysRoleManager,
)
from utils import deployed_easy_track


@pytest.fixture(scope="session")
def deployer(accounts):
    return accounts[2]


@pytest.fixture(scope="session")
def commitee_multisig(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def et_contracts():
    return deployed_easy_track.contracts()


@pytest.fixture(scope="module")
def easytrack_executor(et_contracts, stranger):
    def helper(creator, factory, calldata):
        tx = et_contracts.easy_track.createMotion(
            factory,
            calldata,
            {"from": creator},
        )
        motions = et_contracts.easy_track.getMotions()

        chain.sleep(72 * 60 * 60 + 100)

        et_contracts.easy_track.enactMotion(
            motions[-1][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

    return helper


@pytest.fixture(scope="module")
def add_node_operators_factory(
    et_contracts, voting, commitee_multisig, simple_dvt, deployer, acl
):
    factory = AddNodeOperators.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    add_node_operators_permissions = (
        simple_dvt.address
        + simple_dvt.addNodeOperator.signature[2:]
        + acl.address[2:]
        + acl.grantPermissionP.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory, add_node_operators_permissions, {"from": voting}
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def activate_node_operators_factory(
    et_contracts, voting, commitee_multisig, simple_dvt, deployer
):
    factory = ActivateNodeOperators.deploy(
        commitee_multisig, simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    activate_node_operators_permissions = (
        simple_dvt.address + simple_dvt.activateNodeOperator.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        activate_node_operators_permissions,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def deactivate_node_operators_factory(
    et_contracts, voting, commitee_multisig, simple_dvt, deployer
):
    factory = DeactivateNodeOperators.deploy(
        commitee_multisig, simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    deactivate_node_operators_permissions = (
        simple_dvt.address + simple_dvt.deactivateNodeOperator.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        deactivate_node_operators_permissions,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def set_node_operator_name_factory(
    et_contracts, voting, commitee_multisig, simple_dvt, deployer
):
    factory = SetNodeOperatorNames.deploy(
        commitee_multisig, simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    set_node_operator_name_permissions = (
        simple_dvt.address + simple_dvt.setNodeOperatorName.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        set_node_operator_name_permissions,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def set_node_operator_reward_address_factory(
    et_contracts, voting, commitee_multisig, simple_dvt, deployer
):
    factory = SetNodeOperatorRewardAddresses.deploy(
        commitee_multisig, simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    set_node_operator_name_permissions = (
        simple_dvt.address + simple_dvt.setNodeOperatorRewardAddress.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        set_node_operator_name_permissions,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def increase_vetted_validators_limit_factory(
    et_contracts, voting, simple_dvt, deployer
):
    factory = IncreaseVettedValidatorsLimit.deploy(
        simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt

    increase_vetted_validators_limit_permissions = (
        simple_dvt.address + simple_dvt.setNodeOperatorStakingLimit.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        increase_vetted_validators_limit_permissions,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def increase_node_operators_staking_limit_by_commitee_factory(
    et_contracts, voting, simple_dvt, deployer, commitee_multisig
):
    factory = IncreaseNodeOperatorsStakingLimitByCommitee.deploy(
        commitee_multisig, simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    increase_node_operators_staking_limit_by_commitee_permission = (
        simple_dvt.address + simple_dvt.setNodeOperatorStakingLimit.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        increase_node_operators_staking_limit_by_commitee_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def update_tareget_validators_limits_factory(
    et_contracts, voting, simple_dvt, deployer, commitee_multisig
):
    factory = UpdateTargetValidatorsLimits.deploy(
        commitee_multisig, simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    update_tareget_validators_limits_permission = (
        simple_dvt.address + simple_dvt.updateTargetValidatorsLimits.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        update_tareget_validators_limits_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def transfer_node_operator_manager_factory(
    et_contracts, voting, simple_dvt, deployer, commitee_multisig, acl
):
    factory = TransferNodeOperatorManager.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig
    assert factory.acl() == acl

    transfer_node_operator_manager_permission = (
        acl.address
        + acl.revokePermission.signature[2:]
        + acl.address[2:]
        + acl.grantPermissionP.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        transfer_node_operator_manager_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def renounce_manage_signing_keys_role_manager_factory(
    et_contracts, voting, simple_dvt, deployer, commitee_multisig, acl
):
    factory = RenounceManageSigningKeysRoleManager.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig
    assert factory.acl() == acl

    renounce_manage_signing_keys_role_manager_permission = (
        acl.address + acl.removePermissionManager.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        renounce_manage_signing_keys_role_manager_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory
