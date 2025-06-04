import pytest
from brownie import reverts, CSMSetVettedGateTree, VettedGateStub, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata
from utils.test_helpers import set_account_balance

def create_calldata(tree_root, tree_cid):
    return encode_calldata(["bytes32", "string"], [tree_root, tree_cid])


@pytest.fixture(scope="module")
def vetted_gate_stub(owner):
    """Create a mock VettedGate contract with setTreeParams method"""
    return owner.deploy(VettedGateStub)


@pytest.fixture(scope="module") 
def csm_set_vetted_gate_tree_factory(owner, vetted_gate_stub):
    return CSMSetVettedGateTree.deploy(owner, "IdentifiedCommunityStakerSetTreeParams", vetted_gate_stub, {"from": owner})


def test_deploy(owner, vetted_gate_stub, csm_set_vetted_gate_tree_factory):
    """Must deploy contract with correct data"""
    assert csm_set_vetted_gate_tree_factory.trustedCaller() == owner
    assert csm_set_vetted_gate_tree_factory.vettedGate() == vetted_gate_stub
    assert csm_set_vetted_gate_tree_factory.name() == "IdentifiedCommunityStakerSetTreeParams"


def test_create_evm_script_called_by_stranger(stranger, csm_set_vetted_gate_tree_factory):
    """Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"""
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        csm_set_vetted_gate_tree_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_tree_root(owner, csm_set_vetted_gate_tree_factory):
    """Must revert with message 'EMPTY_TREE_ROOT' when tree root is empty"""
    EMPTY_ROOT_CALLDATA = create_calldata(
        b'\x00' * 32,  # bytes32 zero value
        "test_cid"
    )
    with reverts('EMPTY_TREE_ROOT'):
        csm_set_vetted_gate_tree_factory.createEVMScript(owner, EMPTY_ROOT_CALLDATA)


def test_empty_tree_cid(owner, csm_set_vetted_gate_tree_factory):
    """Must revert with message 'EMPTY_TREE_CID' when tree CID is empty"""
    EMPTY_CID_CALLDATA = create_calldata(
        bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"),
        ""
    )
    with reverts('EMPTY_TREE_CID'):
        csm_set_vetted_gate_tree_factory.createEVMScript(owner, EMPTY_CID_CALLDATA)


def test_create_evm_script(owner, csm_set_vetted_gate_tree_factory, vetted_gate_stub):
    """Must create correct EVMScript if all requirements are met"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"

    EVM_SCRIPT_CALLDATA = create_calldata(tree_root, tree_cid)
    evm_script = csm_set_vetted_gate_tree_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(vetted_gate_stub.address, vetted_gate_stub.setTreeParams.encode_input(tree_root, tree_cid))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(csm_set_vetted_gate_tree_factory):
    """Must decode EVMScript call data correctly"""
    tree_root = bytes.fromhex("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    tree_cid = "QmTest123456789"
    
    EVM_SCRIPT_CALLDATA = create_calldata(tree_root, tree_cid)
    decoded_root, decoded_cid = csm_set_vetted_gate_tree_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert decoded_root == "0x" + tree_root.hex()
    assert decoded_cid == tree_cid
