import pytest
import os
import json
import brownie

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
    IncreaseVettedValidatorsLimit,
)
from utils import deployed_easy_track
from utils.config import get_network_name
from utils.test_helpers import set_account_balance

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

        return etx

    return helper


@pytest.fixture(scope="module")
def easytrack_pair_executor_with_collision(et_contracts, stranger):
    def helper(revert, motion_pair):
        txs = []
        assert len(motion_pair) == 2
        for ind in [0, 1]:
            (creator, factory, calldata) = motion_pair[ind]
            txs.append(
                et_contracts.easy_track.createMotion(
                    factory,
                    calldata,
                    {"from": creator},
                )
            )
            print("creation costs: ", txs[ind].gas_used)

        motions = et_contracts.easy_track.getMotions()
        chain.sleep(72 * 60 * 60 + 100)

        etx = et_contracts.easy_track.enactMotion(
            motions[-2][0],
            txs[-2].events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )
        print("enactment costs: ", etx.gas_used)

        with revert:
            etx = et_contracts.easy_track.enactMotion(
                motions[-1][0],
                txs[-1].events["MotionCreated"]["_evmScriptCallData"],
                {"from": stranger},
            )
            print("enactment costs: ", etx.gas_used)

        et_contracts.easy_track.cancelMotion(motions[-1][0], {"from": creator})

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


@pytest.fixture(scope="module")
def active_cs_module(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    return request.getfixturevalue("cs_module")


@pytest.fixture(scope="module")
def active_curated_module(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    return request.getfixturevalue("curated_module")


@pytest.fixture(scope="module")
def active_nor_module(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    return request.getfixturevalue("node_operators_registry")


@pytest.fixture(scope="module")
def active_cm_meta_registry(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    return request.getfixturevalue("cm_meta_registry")


@pytest.fixture(scope="module")
def active_csm_allowed_merkle_gates_registry(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    return request.getfixturevalue("csm_allowed_merkle_gates_registry")


@pytest.fixture(scope="module")
def active_csm_merkle_gate(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    return request.getfixturevalue("csm_merkle_gate")


@pytest.fixture(scope="module")
def active_staking_router(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    return request.getfixturevalue("staking_router")


@pytest.fixture(scope="module")
def active_sr_consolidation_migrator(request, use_deployed_contracts_from_env):
    if not use_deployed_contracts_from_env:
        return None
    sr_consolidation_migrator = request.getfixturevalue("sr_consolidation_migrator")
    assert (
        sr_consolidation_migrator is not None
    ), "sr_consolidation_migrator is None; fill consolidation_migrator address for selected network"
    return sr_consolidation_migrator


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
def impersonate_account(accounts):
    def _impersonate(address):
        set_account_balance(address)
        return accounts.at(address, force=True)

    return _impersonate


@pytest.fixture(scope="module")
def first_role_holder():
    def _first_role_holder(contract, role):
        count = contract.getRoleMemberCount(role)
        assert count > 0, f"No holders for role {role}"
        return contract.getRoleMember(role, 0)

    return _first_role_holder


@pytest.fixture(scope="module")
def ensure_module_in_staking_router(staking_router, impersonate_account, first_role_holder):
    def _ensure(module, module_name):
        module_address = module.address.lower()
        for module_id in staking_router.getStakingModuleIds():
            module_info = staking_router.getStakingModule(module_id)
            if module_info[1].lower() == module_address:
                return module_id

        manager = first_role_holder(staking_router, staking_router.STAKING_MODULE_MANAGE_ROLE())
        manager_sender = impersonate_account(manager)
        staking_router.addStakingModule(
            module_name,
            module.address,
            10_000,
            10_000,
            500,
            500,
            150,
            25,
            {"from": manager_sender},
        )
        for module_id in staking_router.getStakingModuleIds():
            module_info = staking_router.getStakingModule(module_id)
            if module_info[1].lower() == module_address:
                return module_id
        raise RuntimeError("Failed to add module to staking router")

    return _ensure


@pytest.fixture(scope="module")
def ensure_module_unpaused(impersonate_account, first_role_holder):
    def _ensure(module):
        if not module.isPaused():
            return

        resume_sender = impersonate_account(first_role_holder(module, module.RESUME_ROLE()))
        module.resume({"from": resume_sender})

    return _ensure


@pytest.fixture(scope="module")
def ensure_module_operator(accounts, ensure_module_unpaused, impersonate_account, first_role_holder):
    def _ensure(module):
        count = module.getNodeOperatorsCount()
        if count > 0:
            return 0

        ensure_module_unpaused(module)
        creator = first_role_holder(module, module.CREATE_NODE_OPERATOR_ROLE())
        creator_sender = impersonate_account(creator)
        operator = accounts[0].address
        module.createNodeOperator(
            operator,
            (operator, operator, False),
            operator,
            {"from": creator_sender},
        )
        return module.getNodeOperatorsCount() - 1

    return _ensure


@pytest.fixture(scope="module")
def ensure_legacy_module_operator(accounts, agent, impersonate_account):
    def _ensure(module):
        count = module.getNodeOperatorsCount()
        if count > 0:
            return 0

        module.addNodeOperator(
            "Scenario Operator",
            accounts[0].address,
            {"from": impersonate_account(agent.address)},
        )
        return module.getNodeOperatorsCount() - 1

    return _ensure


@pytest.fixture(scope="module")
def ensure_gate_unpaused(impersonate_account, first_role_holder):
    def _ensure(gate):
        if not gate.isPaused():
            return

        sender = first_role_holder(gate, gate.RESUME_ROLE())
        gate.resume({"from": impersonate_account(sender)})

    return _ensure


@pytest.fixture(scope="module")
def ensure_module_locked_bond(impersonate_account, first_role_holder):
    def _ensure(module, node_operator_id, amount):
        accounting = brownie.interface.IAccounting(module.ACCOUNTING())
        current_locked = accounting.getActualLockedBond(node_operator_id)
        if current_locked > 0:
            return current_locked

        reporter = first_role_holder(module, module.REPORT_GENERAL_DELAYED_PENALTY_ROLE())
        reporter_sender = impersonate_account(reporter)
        module.reportGeneralDelayedPenalty(
            node_operator_id,
            brownie.web3.keccak(text="SCENARIO_PREP"),
            amount,
            "scenario prep",
            {"from": reporter_sender},
        )
        return accounting.getActualLockedBond(node_operator_id)

    return _ensure


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
    steth,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return AddNodeOperators.at(deployed_artifact["AddNodeOperators"]["address"])

    factory = AddNodeOperators.deploy(commitee_multisig, simple_dvt, acl, steth, {"from": deployer})
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    add_node_operators_permissions = (
        simple_dvt.address
        + simple_dvt.addNodeOperator.signature[2:]
        + acl.address[2:]
        + acl.grantPermissionP.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(factory, add_node_operators_permissions, {"from": voting})
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
    if vote_id_from_env or use_deployed_contracts_from_env:
        return ActivateNodeOperators.at(deployed_artifact["ActivateNodeOperators"]["address"])

    factory = ActivateNodeOperators.deploy(commitee_multisig, simple_dvt, acl, {"from": deployer})
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
        return DeactivateNodeOperators.at(deployed_artifact["DeactivateNodeOperators"]["address"])

    factory = DeactivateNodeOperators.deploy(commitee_multisig, simple_dvt, acl, {"from": deployer})
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
        return SetNodeOperatorNames.at(deployed_artifact["SetNodeOperatorNames"]["address"])

    factory = SetNodeOperatorNames.deploy(commitee_multisig, simple_dvt, {"from": deployer})
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    set_node_operator_name_permissions = simple_dvt.address + simple_dvt.setNodeOperatorName.signature[2:]
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
    steth,
):
    if vote_id_from_env or use_deployed_contracts_from_env:
        return SetNodeOperatorRewardAddresses.at(deployed_artifact["SetNodeOperatorRewardAddresses"]["address"])

    factory = SetNodeOperatorRewardAddresses.deploy(commitee_multisig, simple_dvt, steth, {"from": deployer})
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    set_node_operator_name_permissions = simple_dvt.address + simple_dvt.setNodeOperatorRewardAddress.signature[2:]
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
        return SetVettedValidatorsLimits.at(deployed_artifact["SetVettedValidatorsLimits"]["address"])

    factory = SetVettedValidatorsLimits.deploy(commitee_multisig, simple_dvt, {"from": deployer})
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    set_vetted_validators_limit_permission = simple_dvt.address + simple_dvt.setNodeOperatorStakingLimit.signature[2:]
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
        return IncreaseVettedValidatorsLimit.at(deployed_artifact["IncreaseVettedValidatorsLimit"]["address"])

    factory = IncreaseVettedValidatorsLimit.deploy(simple_dvt, {"from": deployer})
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
        return ChangeNodeOperatorManagers.at(deployed_artifact["ChangeNodeOperatorManagers"]["address"])

    factory = ChangeNodeOperatorManagers.deploy(commitee_multisig, simple_dvt, acl, {"from": deployer})
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig
    assert factory.acl() == acl

    change_node_operator_manager_permission = (
        acl.address + acl.revokePermission.signature[2:] + acl.address[2:] + acl.grantPermissionP.signature[2:]
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
def update_target_validator_limits_factory(
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
        return UpdateTargetValidatorLimits.at(deployed_artifact["UpdateTargetValidatorLimits"]["address"])

    factory = UpdateTargetValidatorLimits.deploy(commitee_multisig, simple_dvt, {"from": deployer})
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    update_target_validators_limits_permission = (
        simple_dvt.address + simple_dvt.updateTargetValidatorsLimits['uint256,uint256,uint256'].signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        update_target_validators_limits_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory
