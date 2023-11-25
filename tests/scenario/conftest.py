import pytest
import os
import json

from brownie import (
    chain,
    AddNodeOperators,
    ActivateNodeOperators,
    DeactivateNodeOperators,
    SetNodeOperatorNames,
    SetNodeOperatorRewardAddresses,
    SetVettedValidatorsLimits,
    ChangeNodeOperatorManagers,
    UpdateTargetValidatorLimits,
    IncreaseVettedValidatorsLimits
)
from utils import deployed_easy_track
from utils.config import get_network_name

ENV_VOTE_ID = "VOTE_ID"
ENV_USE_DEPLOYED_CONTRACTS = "USE_DEPLOYED_CONTRACTS"


@pytest.fixture(scope="session")
def deployer(accounts):
    return accounts[2]


@pytest.fixture(scope="session")
def commitee_multisig(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def et_contracts():
    network_name = get_network_name()
    return deployed_easy_track.contracts(network_name)


@pytest.fixture(scope="module")
def easytrack_executor(et_contracts, stranger):
    def helper(creator, factory, calldata):
        tx = et_contracts.easy_track.createMotion(
            factory,
            calldata,
            {"from": creator},
        )

        print("creation costs: ", tx.gas_used)

        motions = et_contracts.easy_track.getMotions()

        chain.sleep(72 * 60 * 60 + 100)

        etx = et_contracts.easy_track.enactMotion(
            motions[-1][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )
        print("enactment costs: ", etx.gas_used)

    return helper


@pytest.fixture(scope="session")
def vote_id_from_env():
    if os.getenv(ENV_VOTE_ID):
        try:
            vote_id = int(os.getenv(ENV_VOTE_ID))
            return vote_id
        except:
            return None
    return None


@pytest.fixture(scope="session")
def use_deployed_contracts_from_env():
    return True if os.getenv(ENV_USE_DEPLOYED_CONTRACTS) else False


@pytest.fixture(scope="session")
def deployed_artifact():
    network_name = get_network_name()
    file_name = f"deployed-{network_name}.json"

    try:
        f = open(file_name)
        return json.load(f)
    except:
        pass


@pytest.fixture(scope="module", autouse=True)
def execute_vote_from_env(vote_id_from_env, lido_contracts):
    if vote_id_from_env:
        print(f"VOTE_ID env var is set, executing voting {vote_id_from_env}")
        lido_contracts.execute_voting(vote_id_from_env)


@pytest.fixture(scope="module")
def add_node_operators_factory(
    et_contracts,
    voting,
    commitee_multisig,
    simple_dvt,
    deployer,
    acl,
    vote_id_from_env,
    deployed_artifact,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return AddNodeOperators.at(deployed_artifact["AddNodeOperators"]["address"])

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
    et_contracts,
    voting,
    commitee_multisig,
    simple_dvt,
    deployer,
    acl,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    print(vote_id_from_env)
    if vote_id_from_env or use_deployed_contracts_from_env:
        return ActivateNodeOperators.at(
            deployed_artifact["ActivateNodeOperators"]["address"]
        )

    factory = ActivateNodeOperators.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    activate_node_operators_permissions = (
        simple_dvt.address
        + simple_dvt.activateNodeOperator.signature[2:]
        + acl.address[2:]
        + acl.grantPermissionP.signature[2:]
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
    et_contracts,
    voting,
    commitee_multisig,
    simple_dvt,
    deployer,
    acl,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return DeactivateNodeOperators.at(
            deployed_artifact["DeactivateNodeOperators"]["address"]
        )

    factory = DeactivateNodeOperators.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    deactivate_node_operators_permissions = (
        simple_dvt.address
        + simple_dvt.deactivateNodeOperator.signature[2:]
        + acl.address[2:]
        + acl.revokePermission.signature[2:]
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
    et_contracts,
    voting,
    commitee_multisig,
    simple_dvt,
    deployer,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return SetNodeOperatorNames.at(
            deployed_artifact["SetNodeOperatorNames"]["address"]
        )

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
    et_contracts,
    voting,
    commitee_multisig,
    simple_dvt,
    deployer,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return SetNodeOperatorRewardAddresses.at(
            deployed_artifact["SetNodeOperatorRewardAddresses"]["address"]
        )

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
def set_vetted_validators_limit_factory(
    et_contracts,
    voting,
    simple_dvt,
    deployer,
    commitee_multisig,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return SetVettedValidatorsLimits.at(
            deployed_artifact["SetVettedValidatorsLimits"]["address"]
        )

    factory = SetVettedValidatorsLimits.deploy(
        commitee_multisig, simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    set_vetted_validators_limit_permission = (
        simple_dvt.address + simple_dvt.setNodeOperatorStakingLimit.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        set_vetted_validators_limit_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def increase_vetted_validators_limit_factory(
    et_contracts,
    voting,
    simple_dvt,
    deployer,
    commitee_multisig,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return IncreaseVettedValidatorsLimits.at(
            deployed_artifact["IncreaseVettedValidatorsLimits"]["address"]
        )

    factory = IncreaseVettedValidatorsLimits.deploy(
        simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt

    increase_vetted_validators_limit_permission = (
        simple_dvt.address + simple_dvt.setNodeOperatorStakingLimit.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        increase_vetted_validators_limit_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def change_node_operator_manager_factory(
    et_contracts,
    voting,
    simple_dvt,
    deployer,
    commitee_multisig,
    acl,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return ChangeNodeOperatorManagers.at(
            deployed_artifact["ChangeNodeOperatorManagers"]["address"]
        )

    factory = ChangeNodeOperatorManagers.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig
    assert factory.acl() == acl

    change_node_operator_manager_permission = (
        acl.address
        + acl.revokePermission.signature[2:]
        + acl.address[2:]
        + acl.grantPermissionP.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        change_node_operator_manager_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def update_tareget_validator_limits_factory(
    et_contracts,
    voting,
    simple_dvt,
    deployer,
    commitee_multisig,
    deployed_artifact,
    vote_id_from_env,
    use_deployed_contracts_from_env,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return UpdateTargetValidatorLimits.at(
            deployed_artifact["UpdateTargetValidatorLimits"]["address"]
        )

    factory = UpdateTargetValidatorLimits.deploy(
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
