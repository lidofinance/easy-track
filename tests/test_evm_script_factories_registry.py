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


def test_can_execute_empty_evm_script(
    owner, stranger, evm_script_factories_registry, node_operators_registry_stub
):
    permissions = node_operators_registry_stub.address + "ae962acf"

    evm_script_factories_registry.addEVMScriptFactory(
        stranger, permissions, {"from": owner}
    )

    assert not evm_script_factories_registry.canExecuteEVMScript(stranger, b"")


def test_can_execute_empty_permissions(
    stranger, evm_script_factories_registry, node_operators_registry_stub
):
    assert not evm_script_factories_registry.canExecuteEVMScript(
        stranger, "0x00000001ff"
    )


def test_can_execute_evm_script(
    owner,
    evm_script_factories_registry,
    node_operators_registry_stub,
    bytes_utils,
):
    permissions = (
        node_operators_registry_stub.address
        + node_operators_registry_stub.setNodeOperatorStakingLimit.signature[2:]
        + node_operators_registry_stub.address[2:]
        + node_operators_registry_stub.getNodeOperator.signature[2:]
    )

    evm_script_calls = [
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                1, 200
            ),
        ),
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.getNodeOperator.encode_input(1, False),
        ),
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.setRewardAddress.encode_input(accounts[1]),
        ),
    ]

    evm_script_factories_registry.addEVMScriptFactory(
        owner, permissions, {"from": owner}
    )

    # apply first permission in the list
    assert evm_script_factories_registry.canExecuteEVMScript(
        owner, encode_call_script([evm_script_calls[0]])
    )
    # apply second permission in the list
    assert evm_script_factories_registry.canExecuteEVMScript(
        owner, encode_call_script([evm_script_calls[1]])
    )

    # apply both permissions in the list in reverse order
    assert evm_script_factories_registry.canExecuteEVMScript(
        owner, encode_call_script([evm_script_calls[1], evm_script_calls[0]])
    )

    # has no rights to run one method
    assert not evm_script_factories_registry.canExecuteEVMScript(
        owner,
        encode_call_script(
            [evm_script_calls[1], evm_script_calls[0], evm_script_calls[2]]
        ),
    )

    # has no rights only one method
    assert not evm_script_factories_registry.canExecuteEVMScript(
        owner, encode_call_script([evm_script_calls[2]])
    )
