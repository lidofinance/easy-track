import pytest
from brownie import reverts, SetMerkleGateTree, MerkleGateStub

from utils.evm_script import encode_call_script, encode_calldata


TEST_FACTORY_NAME = "CSMv3"


def create_calldata(gate, current_tree_root, current_tree_cid, new_tree_root, new_tree_cid):
    return encode_calldata(
        ["address", "bytes32", "string", "bytes32", "string"],
        [gate, current_tree_root, current_tree_cid, new_tree_root, new_tree_cid],
    )


@pytest.fixture(scope="module")
def merkle_gate_stub(owner):
    """Create a mock MerkleGate contract"""
    stub = owner.deploy(MerkleGateStub)
    # Grant SET_TREE_ROLE to owner for testing
    set_tree_role = stub.SET_TREE_ROLE()
    stub.grantRole(set_tree_role, owner, {"from": owner})
    return stub


@pytest.fixture(scope="module")
def set_merkle_gate_tree_factory(owner):
    return SetMerkleGateTree.deploy(owner, TEST_FACTORY_NAME, {"from": owner})


def test_deploy(owner, set_merkle_gate_tree_factory):
    """Must deploy contract with correct data"""
    assert set_merkle_gate_tree_factory.trustedCaller() == owner
    assert set_merkle_gate_tree_factory.name() == TEST_FACTORY_NAME


def test_create_evm_script_called_by_stranger(stranger, set_merkle_gate_tree_factory):
    """Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"""
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        set_merkle_gate_tree_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_tree_root(owner, set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must revert with message 'EMPTY_TREE_ROOT' when tree root is empty"""
    EMPTY_ROOT_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        b'\x00' * 32, "",
        b'\x00' * 32, "test_cid",
    )
    with reverts('EMPTY_TREE_ROOT'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EMPTY_ROOT_CALLDATA)


def test_empty_tree_cid(owner, set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must revert with message 'EMPTY_TREE_CID' when tree CID is empty"""
    EMPTY_CID_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        b'\x00' * 32, "",
        bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"), "",
    )
    with reverts('EMPTY_TREE_CID'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EMPTY_CID_CALLDATA)


def test_same_tree_root(owner, merkle_gate_stub, set_merkle_gate_tree_factory):
    """Must revert with message 'SAME_TREE_ROOT' if new tree root matches the current on-chain value"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    # Set initial tree params
    merkle_gate_stub.setTreeParams(tree_root, tree_cid, {"from": owner})

    # Create calldata with same new tree root as current
    new_tree_cid = "QmTest1234567890"  # Slightly different CID
    EVM_SCRIPT_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        tree_root, tree_cid,
        tree_root, new_tree_cid,
    )
    with reverts('SAME_TREE_ROOT'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)

def test_same_tree_cid(owner, merkle_gate_stub, set_merkle_gate_tree_factory):
    """Must revert with message 'SAME_TREE_CID' if new tree CID matches the current on-chain value"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    # Set initial tree params
    merkle_gate_stub.setTreeParams(tree_root, tree_cid, {"from": owner})

    # Create calldata with same new CID as current
    new_tree_root = bytes.fromhex("abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
    EVM_SCRIPT_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        tree_root, tree_cid,
        new_tree_root, tree_cid,
    )
    with reverts('SAME_TREE_CID'):
        set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


def test_current_tree_root_mismatch(owner, merkle_gate_stub, set_merkle_gate_tree_factory):
    """Must revert with 'CURRENT_VALUES_MISMATCH' when supplied currentTreeRoot differs from on-chain"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    merkle_gate_stub.setTreeParams(tree_root, tree_cid, {"from": owner})

    wrong_current_root = bytes.fromhex("ff" * 32)
    new_tree_root = bytes.fromhex("abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
    new_tree_cid = "QmNewCid"
    EVM_SCRIPT_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        wrong_current_root, tree_cid,
        new_tree_root, new_tree_cid,
    )
    with reverts("CURRENT_VALUES_MISMATCH"):
        set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


def test_current_tree_cid_mismatch(owner, merkle_gate_stub, set_merkle_gate_tree_factory):
    """Must revert with 'CURRENT_VALUES_MISMATCH' when supplied currentTreeCid differs from on-chain"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    merkle_gate_stub.setTreeParams(tree_root, tree_cid, {"from": owner})

    wrong_current_cid = "QmWrongCid"
    new_tree_root = bytes.fromhex("abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
    new_tree_cid = "QmNewCid"
    EVM_SCRIPT_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        tree_root, wrong_current_cid,
        new_tree_root, new_tree_cid,
    )
    with reverts("CURRENT_VALUES_MISMATCH"):
        set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


def test_create_evm_script(owner, set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must create correct EVMScript if all requirements are met"""
    current_tree_root = merkle_gate_stub.treeRoot()
    current_tree_cid = merkle_gate_stub.treeCid()
    new_tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    new_tree_cid = "QmTest123456789"

    EVM_SCRIPT_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        current_tree_root, current_tree_cid,
        new_tree_root, new_tree_cid,
    )
    evm_script = set_merkle_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(merkle_gate_stub.address, merkle_gate_stub.setTreeParams.encode_input(new_tree_root, new_tree_cid))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(set_merkle_gate_tree_factory, merkle_gate_stub):
    """Must decode EVMScript call data correctly"""
    current_tree_root = bytes.fromhex("aabbccdd" * 8)
    current_tree_cid = "QmCurrentCid"
    new_tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    new_tree_cid = "QmTest123456789"

    EVM_SCRIPT_CALLDATA = create_calldata(
        merkle_gate_stub.address,
        current_tree_root, current_tree_cid,
        new_tree_root, new_tree_cid,
    )
    decoded = set_merkle_gate_tree_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert decoded[0] == merkle_gate_stub.address
    assert decoded[1] == "0x" + current_tree_root.hex()
    assert decoded[2] == current_tree_cid
    assert decoded[3] == "0x" + new_tree_root.hex()
    assert decoded[4] == new_tree_cid
