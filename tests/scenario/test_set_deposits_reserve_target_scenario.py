import pytest
import brownie
from brownie import SetDepositsReserveTarget, reverts

from utils.evm_script import encode_calldata


DEPOSITS_RESERVE_TARGET_INCREASE = 10 * 10**18


def create_calldata(deposits_reserve_target):
    return encode_calldata(["uint256"], [deposits_reserve_target])


@pytest.fixture(scope="module")
def lido(lido_contracts):
    return brownie.interface.ILido(lido_contracts.steth.address)


@pytest.fixture(scope="module")
def set_deposits_reserve_target_factory(
    owner,
    commitee_multisig,
    voting,
    agent,
    acl,
    et_contracts,
    lido,
):
    max_deposits_reserve_target = lido.getDepositsReserveTarget() + DEPOSITS_RESERVE_TARGET_INCREASE
    factory = owner.deploy(
        SetDepositsReserveTarget,
        commitee_multisig,
        max_deposits_reserve_target,
        lido,
    )

    buffer_reserve_manager_role = brownie.web3.keccak(text="BUFFER_RESERVE_MANAGER_ROLE").hex()
    evm_script_executor = et_contracts.evm_script_executor.address
    if not acl.hasPermission(
        evm_script_executor,
        lido.address,
        buffer_reserve_manager_role,
    ):
        acl.grantPermission(
            evm_script_executor,
            lido.address,
            buffer_reserve_manager_role,
            {"from": agent},
        )

    permissions = lido.address + lido.setDepositsReserveTarget.signature[2:]
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


def test_set_deposits_reserve_target_via_motion(
    commitee_multisig,
    easytrack_executor,
    lido,
    set_deposits_reserve_target_factory,
):
    initial_deposits_reserve_target = lido.getDepositsReserveTarget()
    new_deposits_reserve_target = initial_deposits_reserve_target + 10**18

    easytrack_executor(
        commitee_multisig,
        set_deposits_reserve_target_factory,
        create_calldata(new_deposits_reserve_target),
    )

    assert lido.getDepositsReserveTarget() == new_deposits_reserve_target


def test_reverts_on_motion_creation_if_target_is_unchanged(
    commitee_multisig,
    et_contracts,
    lido,
    set_deposits_reserve_target_factory,
):
    with reverts("SAME_DEPOSITS_RESERVE_TARGET"):
        et_contracts.easy_track.createMotion(
            set_deposits_reserve_target_factory.address,
            create_calldata(lido.getDepositsReserveTarget()),
            {"from": commitee_multisig},
        )


def test_reverts_on_motion_creation_if_target_is_too_high(
    commitee_multisig,
    et_contracts,
    set_deposits_reserve_target_factory,
):
    with reverts("DEPOSITS_RESERVE_TARGET_TOO_HIGH"):
        et_contracts.easy_track.createMotion(
            set_deposits_reserve_target_factory.address,
            create_calldata(set_deposits_reserve_target_factory.MAX_DEPOSITS_RESERVE_TARGET() + 1),
            {"from": commitee_multisig},
        )


def test_reverts_on_motion_creation_if_creator_is_not_trusted(
    stranger,
    et_contracts,
    set_deposits_reserve_target_factory,
):
    with reverts("CALLER_IS_FORBIDDEN"):
        et_contracts.easy_track.createMotion(
            set_deposits_reserve_target_factory.address,
            create_calldata(set_deposits_reserve_target_factory.MAX_DEPOSITS_RESERVE_TARGET()),
            {"from": stranger},
        )
