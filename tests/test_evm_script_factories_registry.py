import random
from brownie import accounts, reverts, EVMScriptFactoriesRegistry
from utils.test_helpers import access_controll_revert_message


def test_deploy(owner):
    "Must deploy MotionsRegistry contract with correct params"
    contract = owner.deploy(EVMScriptFactoriesRegistry, owner)

    # roles
    assert contract.hasRole(contract.DEFAULT_ADMIN_ROLE(), owner)


def test_add_evm_script_factory_called_without_permissions(
    stranger, evm_script_factories_registry
):
    "Must revert with correct Access Control message if called by address without 'DEFAULT_ADMIN_ROLE'"
    with reverts(access_controll_revert_message(stranger)):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, b"", {"from": stranger}
        )


def test_add_evm_script_factory_empty_permissions(
    owner, stranger, evm_script_factories_registry
):
    "Must revert with message 'INVALID_PERMISSIONS' if called with empty permissions"
    with reverts("INVALID_PERMISSIONS"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, b"", {"from": owner}
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


def test_remove_evm_script_factory(owner, stranger, evm_script_factories_registry):
    "Must remove EVMScript factory from the list of allowed EVMScript factories"
    "and emit EVMScriptFactoryRemoved(_evmScriptFactory) event"
    # add many evm script factories
    evm_script_factories = accounts[3:8]
    permissions = stranger.address + "ffccddee"
    for evm_script_factory in evm_script_factories:
        evm_script_factories_registry.addEVMScriptFactory(
            evm_script_factory, permissions, {"from": owner}
        )

    # remove evm scripts in random order
    # and check that was deleted correct script
    while len(evm_script_factories) > 0:
        index = random.randint(0, len(evm_script_factories) - 1)
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
