import brownie
import pytest
from brownie import reverts

from utils.evm_script import encode_calldata


DEPOSITS_RESERVE_TARGET_INCREASE = 100 * 10**18
MOTION_BUFFER_TIME = 100


def create_calldata(deposits_reserve_target):
    return encode_calldata(["uint256"], [deposits_reserve_target])


@pytest.fixture(scope="module")
def lido(lido_contracts):
    return brownie.interface.ILido(lido_contracts.steth.address)


@pytest.fixture(scope="module")
def set_deposits_reserve_target_factory(
    deployer,
    trusted_caller,
    easy_track,
    lido_contracts,
    lido,
    SetDepositsReserveTarget,
):
    max_deposits_reserve_target = lido.getDepositsReserveTarget() + DEPOSITS_RESERVE_TARGET_INCREASE
    factory = deployer.deploy(
        SetDepositsReserveTarget,
        trusted_caller,
        max_deposits_reserve_target,
        lido,
    )

    buffer_reserve_manager_role = brownie.web3.keccak(text="BUFFER_RESERVE_MANAGER_ROLE").hex()
    evm_script_executor = easy_track.evmScriptExecutor()
    acl = lido_contracts.aragon.acl
    if not acl.hasPermission(
        evm_script_executor,
        lido.address,
        buffer_reserve_manager_role,
    ):
        acl.grantPermission(
            evm_script_executor,
            lido.address,
            buffer_reserve_manager_role,
            {"from": lido_contracts.aragon.agent},
        )

    permissions = lido.address + lido.setDepositsReserveTarget.signature[2:]
    easy_track.addEVMScriptFactory(
        factory,
        permissions,
        {"from": lido_contracts.aragon.voting},
    )

    assert easy_track.isEVMScriptFactory(factory)
    assert factory in easy_track.getEVMScriptFactories()
    return factory


def test_set_deposits_reserve_target_motion_happy_path(
    trusted_caller,
    easy_track,
    enact_motion_by_creation_tx,
    lido,
    set_deposits_reserve_target_factory,
):
    initial_deposits_reserve_target = lido.getDepositsReserveTarget()
    targets = [
        set_deposits_reserve_target_factory.MAX_DEPOSITS_RESERVE_TARGET(),
        0,
    ]

    for new_deposits_reserve_target in targets:
        motions_count_before = len(easy_track.getMotions())
        previous_deposits_reserve_target = lido.getDepositsReserveTarget()

        creation_tx = easy_track.createMotion(
            set_deposits_reserve_target_factory,
            create_calldata(new_deposits_reserve_target),
            {"from": trusted_caller},
        )

        assert len(easy_track.getMotions()) == motions_count_before + 1
        assert lido.getDepositsReserveTarget() == previous_deposits_reserve_target

        brownie.chain.sleep(easy_track.motionDuration() + MOTION_BUFFER_TIME)
        enact_motion_by_creation_tx(creation_tx)

        assert len(easy_track.getMotions()) == motions_count_before
        assert lido.getDepositsReserveTarget() == new_deposits_reserve_target

    assert initial_deposits_reserve_target != targets[0]


def test_factory_permissions_restrict_lido_target(
    deployer,
    trusted_caller,
    easy_track,
    lido_contracts,
    lido,
    set_deposits_reserve_target_factory,
    SetDepositsReserveTarget,
):
    factory = deployer.deploy(
        SetDepositsReserveTarget,
        trusted_caller,
        set_deposits_reserve_target_factory.MAX_DEPOSITS_RESERVE_TARGET(),
        lido,
    )

    wrong_permissions = lido_contracts.aragon.agent.address + lido.setDepositsReserveTarget.signature[2:]
    easy_track.addEVMScriptFactory(
        factory,
        wrong_permissions,
        {"from": lido_contracts.aragon.voting},
    )

    with reverts("HAS_NO_PERMISSIONS"):
        easy_track.createMotion(
            factory,
            create_calldata(set_deposits_reserve_target_factory.MAX_DEPOSITS_RESERVE_TARGET()),
            {"from": trusted_caller},
        )
