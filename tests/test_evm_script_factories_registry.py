import random
import pytest

from brownie.network.state import Chain
from brownie import EasyTrack, accounts, reverts, ZERO_ADDRESS
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants


def test_add_evm_script_factory_called_by_stranger(
    stranger, evm_script_factories_registry
):
    with reverts("Ownable: caller is not the owner"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, b"", {"from": stranger}
        )


def test_add_evm_script_factory_empty_permissions(
    owner, stranger, evm_script_factories_registry
):
    with reverts("INVALID_PERMISSIONS"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, b"", {"from": owner}
        )


def test_add_evm_script_factory_invalid_length(
    owner, stranger, evm_script_factories_registry
):
    with reverts("INVALID_PERMISSIONS"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, "0x0011223344", {"from": owner}
        )


def test_add_evm_script(owner, stranger, evm_script_factories_registry):
    permissions = stranger.address + "ffccddee"
    tx = evm_script_factories_registry.addEVMScriptFactory(
        stranger, permissions, {"from": owner}
    )
    assert tx.events["EVMScriptFactoryAdded"]["_evmScriptFactory"] == stranger
    assert tx.events["EVMScriptFactoryAdded"]["_permissions"] == permissions


def test_add_evm_script_twice(owner, stranger, evm_script_factories_registry):
    permissions = stranger.address + "ffccddee"
    evm_script_factories_registry.addEVMScriptFactory(
        stranger, permissions, {"from": owner}
    )
    with reverts("EVM_SCRIPT_FACTORY_ALREADY_ADDED"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, permissions, {"from": owner}
        )


def test_remove_evm_script_factory_not_found(stranger, evm_script_factories_registry):
    with reverts("EVM_SCRIPT_FACTORY_NOT_FOUND"):
        evm_script_factories_registry.removeEVMScriptFactory(stranger)


def test_remove_evm_script_factory(owner, stranger, evm_script_factories_registry):
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
        evm_script_factories_registry.removeEVMScriptFactory(
            evm_script_factory_to_remove, {"from": owner}
        )

        evm_script_factories_after_remove = (
            evm_script_factories_registry.getEVMScriptFactories()
        )
        assert len(evm_script_factories) == len(evm_script_factories_after_remove)

        len(set(evm_script_factories).union(evm_script_factories_after_remove)) == len(
            evm_script_factories
        )
