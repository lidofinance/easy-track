import pytest
from brownie import reverts
from utils.evm_script import encode_calldata


def create_calldata(gate, tree_root, tree_cid):
    """Helper function to create encoded calldata for setTreeParams"""
    return encode_calldata(["address", "bytes32", "string"], [gate, tree_root, tree_cid])


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
def allowed_gates_registry(
    owner,
    use_deployed_contracts_from_env,
    active_csm_allowed_merkle_gates_registry,
    merkle_gate,
):
    if use_deployed_contracts_from_env:
        return active_csm_allowed_merkle_gates_registry

    from brownie import AllowedMerkleGatesRegistry

    return owner.deploy(
        AllowedMerkleGatesRegistry,
        owner,
        "CSM",
        [merkle_gate],
        ["Scenario Gate"],
    )


@pytest.fixture(scope="module")
def merkle_gate_set_tree_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    allowed_gates_registry,
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
        allowed_gates_registry.address,
    )

    # And add the factory to EasyTrack to activate it. It should be done on CSM v2 voting
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
        # Create EVM script for this update
        evm_script_calldata = create_calldata(merkle_gate.address, update["root"], update["cid"])
        
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
    new_cid = "QmScenarioNewCid123"
    if merkle_gate.treeCid() == new_cid:
        new_cid = "QmScenarioNewCid456"

    evm_script_calldata = create_calldata(
        merkle_gate.address,
        current_root,
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
    current_root = tree_root_hex(merkle_gate.treeRoot())
    current_cid = merkle_gate.treeCid()
    new_root = bytes.fromhex("cd" * 32)
    if current_root == "0x" + new_root.hex():
        new_root = bytes.fromhex("ef" * 32)

    evm_script_calldata = create_calldata(
        merkle_gate.address,
        new_root,
        current_cid,
    )

    with reverts("SAME_TREE_CID"):
        et_contracts.easy_track.createMotion(
            merkle_gate_set_tree_factory.address,
            evm_script_calldata,
            {"from": commitee_multisig},
        )
