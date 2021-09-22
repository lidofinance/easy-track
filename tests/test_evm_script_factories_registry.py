import pytest
import random
from brownie import reverts


@pytest.fixture(scope="module")
def extra_evm_script_factories(accounts):
    return accounts[3:8]


def test_deploy(owner, EVMScriptFactoriesRegistry):
    "Must deploy MotionsRegistry contract with correct params"
    contract = owner.deploy(EVMScriptFactoriesRegistry, owner)
    assert contract.hasRole(contract.DEFAULT_ADMIN_ROLE(), owner)


def test_add_evm_script_factory_called_without_permissions(
    stranger, evm_script_factories_registry, access_controll_revert_message
):
    "Must revert with correct Access Control message if called by address without 'DEFAULT_ADMIN_ROLE'"
    permissions = stranger.address + "ffccddee"
    with reverts(access_controll_revert_message(stranger)):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, permissions, {"from": stranger}
        )


def test_add_evm_script_factory_empty_permissions(
    owner, stranger, evm_script_factories_registry
):
    "Must revert with message 'INVALID_PERMISSIONS' if called with empty permissions"
    with reverts("INVALID_PERMISSIONS"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, "0x", {"from": owner}
        )


def test_add_evm_script_factory_invalid_length(
    owner, stranger, evm_script_factories_registry
):
    "Must revert with message 'INVALID_PERMISSIONS' if called with permissions which have incorrect length"
    with reverts("INVALID_PERMISSIONS"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, "0x0011223344", {"from": owner}
        )


def test_add_evm_script(owner, stranger, evm_script_factories_registry):
    "Must add new EVMScript factory and emit EVMScriptFactoryAdded(_evmScriptFactory, _permissions) event"
    permissions = stranger.address + "ffccddee"
    tx = evm_script_factories_registry.addEVMScriptFactory(
        stranger, permissions, {"from": owner}
    )
    assert tx.events["EVMScriptFactoryAdded"]["_evmScriptFactory"] == stranger
    assert tx.events["EVMScriptFactoryAdded"]["_permissions"] == permissions


def test_add_evm_script_twice(owner, stranger, evm_script_factories_registry):
    "Must revert with message 'EVM_SCRIPT_FACTORY_ALREADY_ADDED'"
    "if called with already listed EVMScript factory address"
    permissions = stranger.address + "ffccddee"
    evm_script_factories_registry.addEVMScriptFactory(
        stranger, permissions, {"from": owner}
    )
    with reverts("EVM_SCRIPT_FACTORY_ALREADY_ADDED"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, permissions, {"from": owner}
        )


def test_remove_evm_script_factory_not_found(
    owner, stranger, evm_script_factories_registry
):
    "Must revert with message 'EVM_SCRIPT_FACTORY_NOT_FOUND'"
    with reverts("EVM_SCRIPT_FACTORY_NOT_FOUND"):
        evm_script_factories_registry.removeEVMScriptFactory(stranger, {"from": owner})


def test_remove_evm_script_factory(
    owner, stranger, evm_script_factories_registry, extra_evm_script_factories
):
    "Must remove EVMScript factory from the list of allowed EVMScript factories"
    "and emit EVMScriptFactoryRemoved(_evmScriptFactory) event"
    # add many evm script factories
    permissions = stranger.address + "ffccddee"
    for evm_script_factory in extra_evm_script_factories:
        evm_script_factories_registry.addEVMScriptFactory(
            evm_script_factory, permissions, {"from": owner}
        )

    # make a copy to avoid modifying the fixture object when popping
    evm_script_factories = extra_evm_script_factories.copy()

    # sets the order in which evm script factories will be removed
    # 1. remove factory at index=3: [0, 1, 2, (3), 4] -> [0, 1, 2, 4]
    # 2. remove factory at index=1: [0, (1), 2, 4] -> [0, 4, 2]
    # 3. remove factory at index=0: [(0), 4, 2] -> [2, 4]
    # 4. remove factory at index=1: [2, (4)]-> [2]
    # 5. remove factory at index=0: [(2)] -> []
    removing_order = [3, 1, 0, 1, 0]

    # remove evm scripts in predefined order and check
    # that was deleted correct evm script factory
    for index in removing_order:
        evm_script_factory_to_remove = evm_script_factories.pop(index)

        assert evm_script_factories_registry.isEVMScriptFactory(
            evm_script_factory_to_remove
        )
        tx = evm_script_factories_registry.removeEVMScriptFactory(
            evm_script_factory_to_remove, {"from": owner}
        )
        assert not evm_script_factories_registry.isEVMScriptFactory(
            evm_script_factory_to_remove
        )

        # validate events
        assert len(tx.events) == 1
        assert (
            tx.events["EVMScriptFactoryRemoved"]["_evmScriptFactory"]
            == evm_script_factory_to_remove
        )

        # validate that was deleted correct address by join
        # test set with resulting set their size must be same
        evm_script_factories_after_remove = (
            evm_script_factories_registry.getEVMScriptFactories()
        )
        assert len(evm_script_factories) == len(evm_script_factories_after_remove)

        len(set(evm_script_factories).union(evm_script_factories_after_remove)) == len(
            evm_script_factories
        )
