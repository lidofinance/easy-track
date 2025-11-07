import pytest
from utils.evm_script import encode_calldata


def create_calldata(tree_root, tree_cid):
    """Helper function to create encoded calldata for setTreeParams"""
    return encode_calldata(["bytes32", "string"], [tree_root, tree_cid])

@pytest.fixture(scope="module")
def merkle_gate_stub(owner, et_contracts):
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
    assert stub.treeRoot() == "0x" + initial_tree_root.hex()
    assert stub.treeCid() == initial_tree_cid

    # Grant SET_TREE_ROLE to the et_contracts.evm_script_executor
    set_tree_role = stub.SET_TREE_ROLE()
    stub.grantRole(set_tree_role, et_contracts.evm_script_executor.address, {"from": owner})

    return stub

@pytest.fixture(scope="module")
def merkle_gate_set_tree_factory(owner, commitee_multisig, voting, et_contracts, merkle_gate_stub):
    """
    Deploy the SetMerkleGateTree factory with the MerkleGateStub
    """
    from brownie import SetMerkleGateTree

    # Deploy SetMerkleGateTree factory
    factory = owner.deploy(
        SetMerkleGateTree,
        commitee_multisig,  # Trusted caller. It should be CSM committee multisig
        "IdentifiedCommunityStakerSetTreeParams",
        merkle_gate_stub.address
    )

    # And add the factory to EasyTrack to activate it. It should be done on CSM v2 voting
    permissions = merkle_gate_stub.address + merkle_gate_stub.setTreeParams.signature[2:]
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting}
    )
    
    return factory


def test_csm_merkle_gate_scenario(
    commitee_multisig,
    merkle_gate_stub,
    merkle_gate_set_tree_factory,
    easytrack_executor,
):
    tree_updates = [
        {
            "root": bytes.fromhex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
            "cid": "QmFirstUpdate123"
        },
        {
            "root": bytes.fromhex("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"),
            "cid": "QmSecondUpdate456"
        },
        {
            "root": bytes.fromhex("cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"),
            "cid": "QmThirdUpdate789"
        }
    ]

    for update in tree_updates:
        # Create EVM script for this update
        evm_script_calldata = create_calldata(update["root"], update["cid"])
        
        easytrack_executor(
            commitee_multisig, merkle_gate_set_tree_factory, evm_script_calldata
        )
        
        # Verify the update was applied
        assert merkle_gate_stub.treeRoot() == "0x" + update["root"].hex()
        assert merkle_gate_stub.treeCid() == update["cid"]
