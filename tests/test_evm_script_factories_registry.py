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
    with reverts(
        "AccessControl: account 0x807c47a89f720fe4ee9b8343c286fc886f43191b is missing role 0x0000000000000000000000000000000000000000000000000000000000000000"
    ):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, b"", {"from": stranger}
        )


def test_add_evm_script_factory_empty_permissions(
    voting, stranger, evm_script_factories_registry
):
    with reverts("INVALID_PERMISSIONS"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, b"", {"from": voting}
        )


def test_add_evm_script_factory_invalid_length(
    voting, stranger, evm_script_factories_registry
):
    with reverts("INVALID_PERMISSIONS"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, "0x0011223344", {"from": voting}
        )


def test_add_evm_script(voting, stranger, evm_script_factories_registry):
    permissions = stranger.address + "ffccddee"
    tx = evm_script_factories_registry.addEVMScriptFactory(
        stranger, permissions, {"from": voting}
    )
    assert tx.events["EVMScriptFactoryAdded"]["_evmScriptFactory"] == stranger
    assert tx.events["EVMScriptFactoryAdded"]["_permissions"] == permissions


def test_add_evm_script_twice(voting, stranger, evm_script_factories_registry):
    permissions = stranger.address + "ffccddee"
    evm_script_factories_registry.addEVMScriptFactory(
        stranger, permissions, {"from": voting}
    )
    with reverts("EVM_SCRIPT_FACTORY_ALREADY_ADDED"):
        evm_script_factories_registry.addEVMScriptFactory(
            stranger, permissions, {"from": voting}
        )


def test_remove_evm_script_factory_not_found(
    voting, stranger, evm_script_factories_registry
):
    with reverts("EVM_SCRIPT_FACTORY_NOT_FOUND"):
        evm_script_factories_registry.removeEVMScriptFactory(stranger, {"from": voting})


def test_remove_evm_script_factory(voting, stranger, evm_script_factories_registry):
    # add many evm script factories
    evm_script_factories = accounts[3:8]
    permissions = stranger.address + "ffccddee"
    for evm_script_factory in evm_script_factories:
        evm_script_factories_registry.addEVMScriptFactory(
            evm_script_factory, permissions, {"from": voting}
        )

    # remove evm scripts in random order
    # and check that was deleted correct script
    while len(evm_script_factories) > 0:
        index = random.randint(0, len(evm_script_factories) - 1)
        evm_script_factory_to_remove = evm_script_factories.pop(index)
        evm_script_factories_registry.removeEVMScriptFactory(
            evm_script_factory_to_remove, {"from": voting}
        )

        evm_script_factories_after_remove = (
            evm_script_factories_registry.getEVMScriptFactories()
        )
        assert len(evm_script_factories) == len(evm_script_factories_after_remove)

        len(set(evm_script_factories).union(evm_script_factories_after_remove)) == len(
            evm_script_factories
        )
