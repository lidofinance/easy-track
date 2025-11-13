import pytest
from brownie import accounts, reverts, ZERO_ADDRESS

from utils.test_helpers import access_revert_message


GATE_TITLE = "New Allowed Merkle Gate"


@pytest.fixture(scope="module")
def merkle_gate_with_interface(owner, MerkleGateStub):
    return owner.deploy(MerkleGateStub)


@pytest.fixture(scope="module")
def allowed_merkle_gates_registry(owner, AllowedMerkleGatesRegistry):
    registry = owner.deploy(AllowedMerkleGatesRegistry, owner)
    return (registry, owner)


def test_registry_initial_state(owner, AllowedMerkleGatesRegistry):
    registry = owner.deploy(AllowedMerkleGatesRegistry, owner)

    # Only admin role is set
    assert registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), owner)

    # Empty list by default
    assert len(registry.getAllowedGates()) == 0


def test_add_gate_success(allowed_merkle_gates_registry, merkle_gate_with_interface):
    registry, admin = allowed_merkle_gates_registry

    tx = registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": admin})

    assert registry.isGateAllowed(merkle_gate_with_interface)
    assert registry.getAllowedGates()[0] == merkle_gate_with_interface
    assert tx.events["GateAdded"]["_gate"] == merkle_gate_with_interface
    assert tx.events["GateAdded"]["_title"] == GATE_TITLE


def test_add_gate_duplicate_reverts(allowed_merkle_gates_registry, merkle_gate_with_interface):
    registry, admin = allowed_merkle_gates_registry

    registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": admin})
    assert registry.isGateAllowed(merkle_gate_with_interface)

    with reverts("GATE_ALREADY_ADDED_TO_ALLOWED_LIST"):
        registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": admin})


def test_remove_gate_success(allowed_merkle_gates_registry, merkle_gate_with_interface):
    registry, admin = allowed_merkle_gates_registry

    registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": admin})
    assert registry.isGateAllowed(merkle_gate_with_interface)

    tx = registry.removeGate(merkle_gate_with_interface, {"from": admin})
    assert not registry.isGateAllowed(merkle_gate_with_interface)
    assert len(registry.getAllowedGates()) == 0
    assert tx.events["GateRemoved"]["_gate"] == merkle_gate_with_interface


def test_remove_not_last_gate_uses_swap_and_pop(allowed_merkle_gates_registry, merkle_gate_with_interface, owner, MerkleGateStub):
    registry, admin = allowed_merkle_gates_registry

    # deploy second gate
    second_gate = owner.deploy(MerkleGateStub)

    registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": admin})
    registry.addGate(second_gate, GATE_TITLE, {"from": admin})

    # Remove the first one; second should be left at index 0
    registry.removeGate(merkle_gate_with_interface, {"from": admin})
    assert registry.getAllowedGates() == [second_gate]


def test_remove_missing_gate_reverts(allowed_merkle_gates_registry, merkle_gate_with_interface):
    registry, admin = allowed_merkle_gates_registry

    with reverts("GATE_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeGate(merkle_gate_with_interface, {"from": admin})


def test_access_control_enforced(owner, stranger, AllowedMerkleGatesRegistry, merkle_gate_with_interface):
    registry = owner.deploy(AllowedMerkleGatesRegistry, owner)

    # Only DEFAULT_ADMIN_ROLE can add/remove
    for caller in [stranger]:
        with reverts(access_revert_message(caller)):
            registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": caller})

    for caller in [stranger]:
        with reverts(access_revert_message(caller)):
            registry.removeGate(merkle_gate_with_interface, {"from": caller})
