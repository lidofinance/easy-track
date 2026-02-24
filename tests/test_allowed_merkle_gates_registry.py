import pytest
from brownie import accounts, history, reverts, ZERO_ADDRESS

from utils.test_helpers import access_revert_message


GATE_TITLE = "New Allowed Merkle Gate"
REGISTRY_NAME = "CSM"


@pytest.fixture(scope="module")
def merkle_gate_with_interface(owner, MerkleGateStub):
    return owner.deploy(MerkleGateStub)


@pytest.fixture(scope="module")
def allowed_merkle_gates_registry(owner, AllowedMerkleGatesRegistry):
    registry = owner.deploy(AllowedMerkleGatesRegistry, owner, REGISTRY_NAME, [], [])
    return (registry, owner)


def test_registry_initial_state(owner, AllowedMerkleGatesRegistry):
    registry = owner.deploy(AllowedMerkleGatesRegistry, owner, REGISTRY_NAME, [], [])

    # Only admin role is set
    assert registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), owner)
    assert registry.name() == REGISTRY_NAME

    # Empty list by default
    assert len(registry.getAllowedGates()) == 0


def test_registry_constructor_seeds_initial_gates(owner, AllowedMerkleGatesRegistry, MerkleGateStub):
    first_gate = owner.deploy(MerkleGateStub)
    second_gate = owner.deploy(MerkleGateStub)
    titles = ["First Gate", "Second Gate"]

    registry = owner.deploy(
        AllowedMerkleGatesRegistry,
        owner,
        REGISTRY_NAME,
        [first_gate, second_gate],
        titles,
    )

    assert registry.name() == REGISTRY_NAME
    assert registry.getAllowedGates() == [first_gate, second_gate]
    assert registry.isGateAllowed(first_gate)
    assert registry.isGateAllowed(second_gate)


def test_registry_constructor_reverts_on_initial_length_mismatch(owner, AllowedMerkleGatesRegistry, MerkleGateStub):
    gate = owner.deploy(MerkleGateStub)
    prev_history_len = len(history)
    with pytest.raises(ValueError, match="not a valid ETH address"):
        owner.deploy(AllowedMerkleGatesRegistry, owner, REGISTRY_NAME, [gate], [])
    assert len(history) == prev_history_len + 1
    assert history[-1].revert_msg == "INITIAL_GATES_AND_TITLES_LENGTH_MISMATCH"


def test_add_gate_success(allowed_merkle_gates_registry, merkle_gate_with_interface):
    registry, admin = allowed_merkle_gates_registry

    tx = registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": admin})

    assert registry.isGateAllowed(merkle_gate_with_interface)
    assert registry.getAllowedGates()[0] == merkle_gate_with_interface
    assert tx.events["GateAdded"]["_gate"] == merkle_gate_with_interface
    assert tx.events["GateAdded"]["_title"] == GATE_TITLE


def test_add_gate_preserves_insertion_order(allowed_merkle_gates_registry, owner, MerkleGateStub):
    registry, admin = allowed_merkle_gates_registry

    gate_list = []
    for _ in range(10):
        gate_list.append(owner.deploy(MerkleGateStub))

    for gate in gate_list:
        registry.addGate(gate, GATE_TITLE, {"from": admin})

    assert registry.getAllowedGates() == gate_list


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


def test_remove_not_last_gate_uses_swap_and_pop(allowed_merkle_gates_registry, owner, MerkleGateStub):
    registry, admin = allowed_merkle_gates_registry

    gate_list = []
    for _ in range(10):
        gate_list.append(owner.deploy(MerkleGateStub))

    for gate in gate_list:
        registry.addGate(gate, GATE_TITLE, {"from": admin})

    def swap_and_pop(gate_list: list, idx):
        gate_list[idx] = gate_list[-1]
        gate_list.pop(-1)

    for idx in (0, 1, 3, 4):
        registry.removeGate(gate_list[idx], {"from": admin})
        swap_and_pop(gate_list, idx)

        assert registry.getAllowedGates() == gate_list


def test_remove_missing_gate_reverts(allowed_merkle_gates_registry, merkle_gate_with_interface):
    registry, admin = allowed_merkle_gates_registry

    with reverts("GATE_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeGate(merkle_gate_with_interface, {"from": admin})


def test_access_control_enforced(owner, stranger, AllowedMerkleGatesRegistry, merkle_gate_with_interface):
    registry = owner.deploy(AllowedMerkleGatesRegistry, owner, REGISTRY_NAME, [], [])

    # Only DEFAULT_ADMIN_ROLE can add/remove
    for caller in [stranger]:
        with reverts(access_revert_message(caller)):
            registry.addGate(merkle_gate_with_interface, GATE_TITLE, {"from": caller})

    for caller in [stranger]:
        with reverts(access_revert_message(caller)):
            registry.removeGate(merkle_gate_with_interface, {"from": caller})
