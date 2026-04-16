import pytest
from brownie import reverts
from utils.evm_script import encode_calldata


def create_calldata(gate, current_tree_root, current_tree_cid, new_tree_root, new_tree_cid):
    """Helper function to create encoded calldata for setTreeParams"""
    return encode_calldata(
        ["address", "bytes32", "string", "bytes32", "string"],
        [gate, current_tree_root, current_tree_cid, new_tree_root, new_tree_cid],
    )


def tree_root_hex(tree_root):
    assert isinstance(tree_root, bytes)
    return "0x" + tree_root.hex()


@pytest.fixture(scope="module")
def merkle_gate(
    owner,
    et_contracts,
    use_deployed_contracts_from_env,
    active_csm_merkle_gate,
    ensure_gate_unpaused,
):
    if use_deployed_contracts_from_env:
        ensure_gate_unpaused(active_csm_merkle_gate)
        return active_csm_merkle_gate

    """
    Create a mock MerkleGate contract with setTreeParams method
    and grant SET_TREE_ROLE to the owner for testing.
    """
    from brownie import MerkleGateStub

    stub = owner.deploy(MerkleGateStub)

    # Initial tree parameters
    initial_tree_root = bytes.fromhex("1111111111111111111111111111111111111111111111111111111111111111")
    initial_tree_cid = "QmInitialTree123456789abcdef"
    stub.setTreeParams(initial_tree_root, initial_tree_cid, {"from": owner})
    assert tree_root_hex(stub.treeRoot()) == "0x" + initial_tree_root.hex()
    assert stub.treeCid() == initial_tree_cid

    # Grant SET_TREE_ROLE to the et_contracts.evm_script_executor
    set_tree_role = stub.SET_TREE_ROLE()
    stub.grantRole(set_tree_role, et_contracts.evm_script_executor.address, {"from": owner})

    return stub


@pytest.fixture(scope="module")
def merkle_gate_set_tree_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    merkle_gate,
):
    """
    Deploy the SetMerkleGateTree factory with the MerkleGateStub
    """
    from brownie import SetMerkleGateTree

    factory = owner.deploy(
        SetMerkleGateTree,
        commitee_multisig,  # Trusted caller. It should be CSM committee multisig
        "CSMv3",
    )

    # And add the factory to EasyTrack to activate it. It should be done on CSM v2 voting
    # Permissions define which gates the factory is allowed to call
    permissions = merkle_gate.address + merkle_gate.setTreeParams.signature[2:]
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting}
    )

    return factory


def test_merkle_gate_scenario(
    commitee_multisig,
    merkle_gate,
    merkle_gate_set_tree_factory,
    easytrack_executor,
):
    current_root = tree_root_hex(merkle_gate.treeRoot())
    current_cid = merkle_gate.treeCid()
    tree_updates = [
        {
            "root": bytes.fromhex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            if current_root != "0x" + "aa" * 32
            else bytes.fromhex("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"),
            "cid": "QmFirstUpdate123" if current_cid != "QmFirstUpdate123" else "QmFirstUpdate456",
        },
    ]

    for update in tree_updates:
        # Fetch current on-chain values for staleness guard
        current_root = merkle_gate.treeRoot()
        current_cid = merkle_gate.treeCid()
        # Create EVM script for this update
        evm_script_calldata = create_calldata(
            merkle_gate.address, current_root, current_cid, update["root"], update["cid"]
        )
        
        easytrack_executor(
            commitee_multisig, merkle_gate_set_tree_factory, evm_script_calldata
        )
        
        # Verify the update was applied
        assert tree_root_hex(merkle_gate.treeRoot()) == "0x" + update["root"].hex()
        assert merkle_gate.treeCid() == update["cid"]


def test_merkle_gate_reverts_with_same_tree_root_on_motion_creation(
    commitee_multisig,
    et_contracts,
    merkle_gate,
    merkle_gate_set_tree_factory,
):
    current_root = merkle_gate.treeRoot()
    current_cid = merkle_gate.treeCid()
    new_cid = "QmScenarioNewCid123"
    if current_cid == new_cid:
        new_cid = "QmScenarioNewCid456"

    evm_script_calldata = create_calldata(
        merkle_gate.address,
        current_root,
        current_cid,
        current_root,  # same root → should revert
        new_cid,
    )

    with reverts("SAME_TREE_ROOT"):
        et_contracts.easy_track.createMotion(
            merkle_gate_set_tree_factory.address,
            evm_script_calldata,
            {"from": commitee_multisig},
        )


def test_merkle_gate_reverts_with_same_tree_cid_on_motion_creation(
    commitee_multisig,
    et_contracts,
    merkle_gate,
    merkle_gate_set_tree_factory,
):
    current_root = merkle_gate.treeRoot()
    current_cid = merkle_gate.treeCid()
    new_root = bytes.fromhex("cd" * 32)
    if tree_root_hex(current_root) == "0x" + new_root.hex():
        new_root = bytes.fromhex("ef" * 32)

    evm_script_calldata = create_calldata(
        merkle_gate.address,
        current_root,
        current_cid,
        new_root,
        current_cid,  # same CID → should revert
    )

    with reverts("SAME_TREE_CID"):
        et_contracts.easy_track.createMotion(
            merkle_gate_set_tree_factory.address,
            evm_script_calldata,
            {"from": commitee_multisig},
        )


def test_merkle_gate_reverts_for_gate_not_in_permissions(
    owner,
    commitee_multisig,
    et_contracts,
    merkle_gate_set_tree_factory,
):
    """Motion creation must revert with HAS_NO_PERMISSIONS when targeting a gate
    that is not listed in the factory's Easy Track permissions."""
    from brownie import MerkleGateStub

    # Deploy a second gate — NOT added to factory permissions
    unpermitted_gate = owner.deploy(MerkleGateStub)
    initial_root = bytes.fromhex("22" * 32)
    initial_cid = "QmUnpermittedInitial"
    unpermitted_gate.setTreeParams(initial_root, initial_cid, {"from": owner})

    new_root = bytes.fromhex("33" * 32)
    new_cid = "QmUnpermittedNew"
    evm_script_calldata = create_calldata(
        unpermitted_gate.address, initial_root, initial_cid, new_root, new_cid
    )

    with reverts("HAS_NO_PERMISSIONS"):
        et_contracts.easy_track.createMotion(
            merkle_gate_set_tree_factory.address,
            evm_script_calldata,
            {"from": commitee_multisig},
        )


def test_merkle_gate_permissions_update_adds_new_gate(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    merkle_gate,
    merkle_gate_set_tree_factory,
    easytrack_executor,
):
    """After updating factory permissions to include a new gate,
    motions targeting the new gate must succeed."""
    from brownie import MerkleGateStub

    # Deploy a new gate
    new_gate = owner.deploy(MerkleGateStub)
    initial_root = bytes.fromhex("44" * 32)
    initial_cid = "QmNewGateInitial"
    new_gate.setTreeParams(initial_root, initial_cid, {"from": owner})

    # Grant SET_TREE_ROLE to the EVM script executor
    set_tree_role = new_gate.SET_TREE_ROLE()
    new_gate.grantRole(set_tree_role, et_contracts.evm_script_executor.address, {"from": owner})

    # Update factory permissions: remove + re-add with both gates
    et_contracts.easy_track.removeEVMScriptFactory(
        merkle_gate_set_tree_factory.address,
        {"from": voting},
    )

    selector = merkle_gate.setTreeParams.signature[2:]
    permissions = (
        merkle_gate.address + selector
        + new_gate.address[2:] + selector
    )
    et_contracts.easy_track.addEVMScriptFactory(
        merkle_gate_set_tree_factory.address,
        permissions,
        {"from": voting},
    )

    # Now a motion for the new gate should succeed
    new_root = bytes.fromhex("55" * 32)
    new_cid = "QmNewGateUpdated"
    evm_script_calldata = create_calldata(
        new_gate.address, initial_root, initial_cid, new_root, new_cid
    )

    easytrack_executor(
        commitee_multisig, merkle_gate_set_tree_factory, evm_script_calldata
    )

    assert tree_root_hex(new_gate.treeRoot()) == "0x" + new_root.hex()
    assert new_gate.treeCid() == new_cid


def test_merkle_gate_permissions_update_removes_gate(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    merkle_gate,
    merkle_gate_set_tree_factory,
):
    """After removing a gate from factory permissions,
    motions targeting that gate must revert with HAS_NO_PERMISSIONS."""
    from brownie import MerkleGateStub

    # Deploy a gate, add it to permissions
    removable_gate = owner.deploy(MerkleGateStub)
    initial_root = bytes.fromhex("66" * 32)
    initial_cid = "QmRemovableGateInitial"
    removable_gate.setTreeParams(initial_root, initial_cid, {"from": owner})

    selector = merkle_gate.setTreeParams.signature[2:]

    # Re-register factory with both gates
    et_contracts.easy_track.removeEVMScriptFactory(
        merkle_gate_set_tree_factory.address,
        {"from": voting},
    )
    et_contracts.easy_track.addEVMScriptFactory(
        merkle_gate_set_tree_factory.address,
        merkle_gate.address + selector + removable_gate.address[2:] + selector,
        {"from": voting},
    )

    # Now remove the removable gate from permissions (keep only merkle_gate)
    et_contracts.easy_track.removeEVMScriptFactory(
        merkle_gate_set_tree_factory.address,
        {"from": voting},
    )
    et_contracts.easy_track.addEVMScriptFactory(
        merkle_gate_set_tree_factory.address,
        merkle_gate.address + selector,
        {"from": voting},
    )

    # Motion targeting the removed gate must now fail
    new_root = bytes.fromhex("77" * 32)
    new_cid = "QmRemovableGateNew"
    evm_script_calldata = create_calldata(
        removable_gate.address, initial_root, initial_cid, new_root, new_cid
    )

    with reverts("HAS_NO_PERMISSIONS"):
        et_contracts.easy_track.createMotion(
            merkle_gate_set_tree_factory.address,
            evm_script_calldata,
            {"from": commitee_multisig},
        )
