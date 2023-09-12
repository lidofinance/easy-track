import pytest
from eth_abi import encode_single
from brownie import (
    web3,
    interface,
    ZERO_ADDRESS,
    AddNodeOperators,
    chain,
    ActivateNodeOperators,
    DeactivateNodeOperators,
    SetNodeOperatorName,
    SetNodeOperatorRewardAddress,
    IncreaseNodeOperatorStakingLimitWithManager,
    convert,
    IncreaseNodeOperatorsStakingLimitByCommitee,
    UpdateTargetValidatorsLimits,
    GrantManageSigningKeysRole,
    RevokeManageSigningKeysRole,
    RenounceManageSigningKeysRoleManager,
)
from utils.evm_script import encode_call_script
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
    et_contracts, voting, commitee_multisig, simple_dvt, deployer
):
    factory = AddNodeOperators.deploy(commitee_multisig, simple_dvt, {"from": deployer})
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig

    add_node_operators_permissions = (
        simple_dvt.address + simple_dvt.addNodeOperator.signature[2:]
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
    factory = SetNodeOperatorName.deploy(
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
    factory = SetNodeOperatorRewardAddress.deploy(
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
def increase_node_operator_staking_limit_with_manager_factory(
    et_contracts, voting, simple_dvt, deployer
):
    factory = IncreaseNodeOperatorStakingLimitWithManager.deploy(
        simple_dvt, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt

    increase_node_operator_staking_limit_with_manager_permissions = (
        simple_dvt.address + simple_dvt.setNodeOperatorStakingLimit.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        increase_node_operator_staking_limit_with_manager_permissions,
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
def grant_manage_signing_keys_role_factory(
    et_contracts, voting, simple_dvt, deployer, commitee_multisig, acl
):
    factory = GrantManageSigningKeysRole.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig
    assert factory.acl() == acl

    grant_manage_signing_keys_role_permission = (
        acl.address + acl.grantPermissionP.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        grant_manage_signing_keys_role_permission,
        {"from": voting},
    )
    evm_script_factories = et_contracts.easy_track.getEVMScriptFactories()
    assert evm_script_factories[-1] == factory

    return factory


@pytest.fixture(scope="module")
def revoke_manage_signing_keys_role_factory(
    et_contracts, voting, simple_dvt, deployer, commitee_multisig, acl
):
    factory = RevokeManageSigningKeysRole.deploy(
        commitee_multisig, simple_dvt, acl, {"from": deployer}
    )
    assert factory.nodeOperatorsRegistry() == simple_dvt
    assert factory.trustedCaller() == commitee_multisig
    assert factory.acl() == acl

    revoke_manage_signing_keys_role_permission = (
        acl.address + acl.revokePermission.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory,
        revoke_manage_signing_keys_role_permission,
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


clusters = [
    {
        "address": "0x000000000000000000000000000000000000000" + str(i),
        "manager": "0x000000000000000000000000000000000000001" + str(i),
        "name": "Cluster " + str(i),
    }
    for i in range(1, 10)
]

signing_keys = {
    "pubkeys": [
        "8bb1db218877a42047b953bdc32573445a78d93383ef5fd08f79c066d4781961db4f5ab5a7cc0cf1e4cbcc23fd17f9d7",
        "884b147305bcd9fce3a1cc12e8f893c6356c1780688286277656e1ba724a3fde49262c98503141c0925b344a8ccea9ca",
        "952ff22cf4a5f9708d536acb2170f83c137301515df5829adc28c265373487937cc45e8f91743caba0b9ebd02b3b664f",
    ],
    "signatures": [
        "ad17ef7cdf0c4917aaebc067a785b049d417dda5d4dd66395b21bbd50781d51e28ee750183eca3d32e1f57b324049a06135ad07d1aa243368bca9974e25233f050e0d6454894739f87faace698b90ea65ee4baba2758772e09fec4f1d8d35660",
        "9794e7871dc766c2139f9476234bc29784e13b51e859445044d2a5a9df8bc072d9c51c51ee69490ce37bdfc7cf899af2166b0710d620a87398d5ec7da06c9f7eb27f1d729973efd60052dbd4cb7f43ff6b141af4d0a0a980b60f663f39bf7844",
        "90111fb6944ff8b56eb0858c1deb91f41c8c631573f4c821663d7079e5e78903d67fa1c4a4ed358378f16a2b7ec524c5196b1a1eae35b01dca1df74535f45d6bd1960164a41425b2a289d4bb5c837049acf5871a0ed23598df42f6234276f6e2",
    ],
}


@pytest.fixture(scope="module")
def simple_dvt(
    node_operators_registry,
    kernel,
    voting,
    locator,
    staking_router,
    agent,
    acl,
):
    nor_proxy = interface.AragonAppProxy(node_operators_registry)
    module_name = "simple-dvt-registry"
    name = web3.keccak(text=module_name).hex()
    simple_DVT_tx = kernel.newAppInstance(
        name, nor_proxy.implementation(), {"from": voting}
    )

    simple_dvt_contract = interface.NodeOperatorsRegistry(
        simple_DVT_tx.new_contracts[0]
    )

    simple_dvt_contract.initialize(locator, "0x01", 0, {"from": voting})

    staking_router.grantRole(
        web3.keccak(text="STAKING_MODULE_MANAGE_ROLE").hex(), agent, {"from": agent}
    )

    staking_router.addStakingModule(
        "Simple DVT", simple_dvt_contract, 10_000, 500, 500, {"from": agent}
    )

    acl.createPermission(
        agent,
        simple_dvt_contract,
        web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE").hex(),
        agent,
        {"from": voting},
    )

    return simple_dvt_contract


def test_simple_dvt_scenario(
    simple_dvt,
    voting,
    commitee_multisig,
    et_contracts,
    acl,
    agent,
    easytrack_executor,
    add_node_operators_factory,
    activate_node_operators_factory,
    deactivate_node_operators_factory,
    set_node_operator_name_factory,
    set_node_operator_reward_address_factory,
    increase_node_operator_staking_limit_with_manager_factory,
    increase_node_operators_staking_limit_by_commitee_factory,
    update_tareget_validators_limits_factory,
    grant_manage_signing_keys_role_factory,
    revoke_manage_signing_keys_role_factory,
    renounce_manage_signing_keys_role_manager_factory,
):
    # Grant roles
    acl.grantPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.MANAGE_NODE_OPERATOR_ROLE(),
        {"from": agent},
    )
    acl.createPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.SET_NODE_OPERATOR_LIMIT_ROLE(),
        agent,
        {"from": voting},
    )
    acl.createPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.MANAGE_SIGNING_KEYS(),
        et_contracts.evm_script_executor,
        {"from": voting},
    )
    acl.createPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.STAKING_ROUTER_ROLE(),
        agent,
        {"from": voting},
    )

    # Add clusters
    add_node_operators_calldata = (
        "0x"
        + encode_single(
            "((string,address)[])",
            [[(cluster["name"], cluster["address"]) for cluster in clusters]],
        ).hex()
    )

    easytrack_executor(
        commitee_multisig, add_node_operators_factory, add_node_operators_calldata
    )

    for cluster_index in range(len(clusters)):
        cluster = simple_dvt.getNodeOperator(cluster_index, True)
        assert cluster["active"] == True
        assert cluster["name"] == clusters[cluster_index]["name"]
        assert cluster["rewardAddress"] == clusters[cluster_index]["address"]
        assert cluster["totalVettedValidators"] == 0
        assert cluster["totalExitedValidators"] == 0
        assert cluster["totalAddedValidators"] == 0
        assert cluster["totalDepositedValidators"] == 0

    # Deactivate node operators with ids 2,3,4

    deactivate_node_operators_calldata = (
        "0x" + encode_single("(uint256[])", [[2, 3, 4]]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        deactivate_node_operators_factory,
        deactivate_node_operators_calldata,
    )

    for cluster_index in range(2, 5):
        cluster = simple_dvt.getNodeOperator(cluster_index, True)
        assert cluster["active"] == False

    # Activate node operators with ids 2,3,4

    activate_node_operators_calldata = (
        "0x" + encode_single("(uint256[])", [[2, 3, 4]]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        activate_node_operators_factory,
        activate_node_operators_calldata,
    )

    for cluster_index in range(2, 5):
        cluster = simple_dvt.getNodeOperator(cluster_index, True)
        assert cluster["active"] == True

    # Set name of node operator

    set_node_operator_name_calldata = (
        "0x" + encode_single("(uint256,string)", [6, "New Name"]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        set_node_operator_name_factory,
        set_node_operator_name_calldata,
    )

    cluster = simple_dvt.getNodeOperator(6, True)
    assert cluster["name"] == "New Name"

    # Set reward address of node operator
    new_reward_address = "0x000000000000000000000000000000000000dEaD"
    set_node_operator_reward_address_calldata = (
        "0x" + encode_single("(uint256,address)", [6, new_reward_address]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        set_node_operator_reward_address_factory,
        set_node_operator_reward_address_calldata,
    )

    cluster = simple_dvt.getNodeOperator(6, True)
    assert cluster["rewardAddress"] == new_reward_address

    # add signing keys to node operator
    no_5_id = 5
    no_5 = simple_dvt.getNodeOperator(no_5_id, False)

    simple_dvt.addSigningKeysOperatorBH(
        no_5_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": no_5["rewardAddress"]},
    )

    assert cluster["totalVettedValidators"] == 0

    # Increase staking limit from NO
    increase_node_operator_staking_limit_with_manager_calldata = (
        "0x" + encode_single("(uint256,uint256)", [no_5_id, 1]).hex()
    )

    easytrack_executor(
        no_5["rewardAddress"],
        increase_node_operator_staking_limit_with_manager_factory,
        increase_node_operator_staking_limit_with_manager_calldata,
    )

    cluster = simple_dvt.getNodeOperator(no_5_id, False)
    assert cluster["totalVettedValidators"] == 1

    # Increase staking limit from manager
    grant_manage_signing_keys_role_calldata = (
        "0x"
        + encode_single(
            "((uint256,address)[])", [[(no_5_id, clusters[no_5_id]["manager"])]]
        ).hex()
    )

    easytrack_executor(
        commitee_multisig,
        grant_manage_signing_keys_role_factory,
        grant_manage_signing_keys_role_calldata,
    )

    # permission parameter
    id8 = 0  # first arg
    op8 = 1  # EQ
    value240 = no_5_id
    permission_param = convert.to_uint(
        (id8 << 248) + (op8 << 240) + value240, "uint256"
    )

    assert simple_dvt.canPerform(
        clusters[no_5_id]["manager"],
        simple_dvt.MANAGE_SIGNING_KEYS(),
        [permission_param],
    )

    increase_node_operator_staking_limit_with_manager_calldata = (
        "0x" + encode_single("(uint256,uint256)", [no_5_id, 2]).hex()
    )

    easytrack_executor(
        clusters[no_5_id]["manager"],
        increase_node_operator_staking_limit_with_manager_factory,
        increase_node_operator_staking_limit_with_manager_calldata,
    )

    cluster = simple_dvt.getNodeOperator(no_5_id, False)
    assert cluster["totalVettedValidators"] == 2

    # Increase staking limit with commitee
    simple_dvt.addSigningKeysOperatorBH(
        no_5_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": no_5["rewardAddress"]},
    )

    no_6_id = 6
    no_6 = simple_dvt.getNodeOperator(no_6_id, False)
    simple_dvt.addSigningKeysOperatorBH(
        no_6_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": no_6["rewardAddress"]},
    )

    increase_node_operators_staking_limit_by_commitee_calldata = (
        "0x"
        + encode_single("((uint256,uint256)[])", [[(no_5_id, 4), (no_6_id, 3)]]).hex()
    )
    easytrack_executor(
        commitee_multisig,
        increase_node_operators_staking_limit_by_commitee_factory,
        increase_node_operators_staking_limit_by_commitee_calldata,
    )

    cluster_5 = simple_dvt.getNodeOperator(no_5_id, False)
    assert cluster_5["totalVettedValidators"] == 4
    cluster_6 = simple_dvt.getNodeOperator(no_6_id, False)
    assert cluster_6["totalVettedValidators"] == 3

    # Update target validators limits

    update_tareget_validators_limits_calldata = (
        "0x"
        + encode_single(
            "((uint256,bool,uint256)[])", [[(no_5_id, True, 1), (no_6_id, True, 10)]]
        ).hex()
    )
    easytrack_executor(
        commitee_multisig,
        update_tareget_validators_limits_factory,
        update_tareget_validators_limits_calldata,
    )

    # Check it somehow

    # Revoke MANAGE_SIGNING_KEYS role

    # Increase staking limit from manager
    revoke_manage_signing_keys_role_calldata = (
        "0x"
        + encode_single(
            "((uint256,address)[])", [[(no_5_id, clusters[no_5_id]["manager"])]]
        ).hex()
    )

    easytrack_executor(
        commitee_multisig,
        revoke_manage_signing_keys_role_factory,
        revoke_manage_signing_keys_role_calldata,
    )

    # permission parameter
    id8 = 0  # first arg
    op8 = 1  # EQ
    value240 = no_5_id
    permission_param = convert.to_uint(
        (id8 << 248) + (op8 << 240) + value240, "uint256"
    )

    assert not simple_dvt.canPerform(
        clusters[no_5_id]["manager"],
        simple_dvt.MANAGE_SIGNING_KEYS(),
        [permission_param],
    )

    # Renounce MANAGE_SIGNING_KEYS role manager

    easytrack_executor(
        commitee_multisig,
        renounce_manage_signing_keys_role_manager_factory,
        "",
    )

    assert (
        acl.getPermissionManager(
            clusters[no_5_id]["manager"], simple_dvt.MANAGE_SIGNING_KEYS()
        )
        == ZERO_ADDRESS
    )
