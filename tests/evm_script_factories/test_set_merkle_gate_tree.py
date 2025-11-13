import pytest
from brownie import reverts, SetMerkleGateTree, MerkleGateStub, AllowedMerkleGatesRegistry, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata
from utils.test_helpers import set_account_balance

def create_calldata(gate, tree_root, tree_cid):
    return encode_calldata(["address", "bytes32", "string"], [gate, tree_root, tree_cid])


@pytest.fixture(scope="module")
def merkle_gate_stub(owner):
    """Create a mock MerkleGate contract"""
    stub = owner.deploy(MerkleGateStub)
    # Grant SET_TREE_ROLE to owner for testing
    set_tree_role = stub.SET_TREE_ROLE()
    stub.grantRole(set_tree_role, owner, {"from": owner})
    return stub


@pytest.fixture(scope="module")
def allowed_gates_registry(owner, merkle_gate_stub):
    registry = owner.deploy(AllowedMerkleGatesRegistry, owner)
    registry.addGate(merkle_gate_stub, "Test Gate", {"from": owner})
    return registry


@pytest.fixture(scope="module") 
def set_merkle_gate_tree_factory(owner, allowed_gates_registry):
    return SetMerkleGateTree.deploy(owner, allowed_gates_registry, {"from": owner})


def test_deploy(owner, allowed_gates_registry, set_merkle_gate_tree_factory):
    """Must deploy contract with correct data"""
    assert set_merkle_gate_tree_factory.trustedCaller() == owner
    assert set_merkle_gate_tree_factory.allowedMerkleGatesRegistry() == allowed_gates_registry


def test_create_evm_script_called_by_stranger(stranger, set_merkle_gate_tree_factory):
    """Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"""
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_merkle_gate_tree_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_tree_root(owner, set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must revert with message 'EMPTY_TREE_ROOT' when tree root is empty"""
    EMPTY_ROOT_CALLDATA = create_calldata(merkle_gate_stub.address, b'\x00' * 32, "test_cid")
    with reverts('EMPTY_TREE_ROOT'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EMPTY_ROOT_CALLDATA)


def test_empty_tree_cid(owner, set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must revert with message 'EMPTY_TREE_CID' when tree CID is empty"""
    EMPTY_CID_CALLDATA = create_calldata(merkle_gate_stub.address, bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"), "")
    with reverts('EMPTY_TREE_CID'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EMPTY_CID_CALLDATA)


def test_same_tree_root(owner, merkle_gate_stub, set_merkle_gate_tree_factory):
    """Must revert with message 'SAME_TREE_ROOT' if tree params are the same as the last set"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    # Set initial tree params
    merkle_gate_stub.setTreeParams(tree_root, tree_cid, {"from": owner})

    # Create calldata for the same tree root
    new_tree_cid = "QmTest1234567890"  # Slightly different CID
    EVM_SCRIPT_CALLDATA = create_calldata(merkle_gate_stub.address, tree_root, new_tree_cid)
    with reverts('SAME_TREE_ROOT'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

def test_same_tree_cid(owner, merkle_gate_stub, set_merkle_gate_tree_factory):
    """Must revert with message 'SAME_TREE_CID' if tree params are the same as the last set"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    # Set initial tree params
    merkle_gate_stub.setTreeParams(tree_root, tree_cid, {"from": owner})

    # Create calldata for the same CID
    new_tree_root = bytes.fromhex("abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
    EVM_SCRIPT_CALLDATA = create_calldata(merkle_gate_stub.address, new_tree_root, tree_cid)
    with reverts('SAME_TREE_CID'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


def test_create_evm_script(owner, set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must create correct EVMScript if all requirements are met"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"

    EVM_SCRIPT_CALLDATA = create_calldata(merkle_gate_stub.address, tree_root, tree_cid)
    evm_script = set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(merkle_gate_stub.address, merkle_gate_stub.setTreeParams.encode_input(tree_root, tree_cid))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must decode EVMScript call data correctly"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    
    EVM_SCRIPT_CALLDATA = create_calldata(merkle_gate_stub.address, tree_root, tree_cid)
    decoded_gate, decoded_root, decoded_cid = set_merkle_gate_tree_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert decoded_gate == merkle_gate_stub.address
    assert decoded_root == "0x" + tree_root.hex()
    assert decoded_cid == tree_cid
