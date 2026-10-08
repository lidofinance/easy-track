import pytest
from scripts.deploy_core_easy_track_contracts import deploy_core_easy_track_contracts
from utils import constants
from utils.test_helpers import CANCEL_ROLE, DEFAULT_ADMIN_ROLE, PAUSE_ROLE, UNPAUSE_ROLE

ROLES = {
    "DEFAULT_ADMIN_ROLE": DEFAULT_ADMIN_ROLE,
    "PAUSE_ROLE": PAUSE_ROLE,
    "UNPAUSE_ROLE": UNPAUSE_ROLE,
    "CANCEL_ROLE": CANCEL_ROLE,
}


def role_holders(easy_track, candidates):
    return {
        name: {account for account in candidates if easy_track.hasRole(role, account)} for name, role in ROLES.items()
    }


def deploy(lido_contracts, deployer, admin, **optional_roles):
    return deploy_core_easy_track_contracts(
        admin=admin,
        governance_token=lido_contracts.ldo,
        aragon_calls_script=lido_contracts.aragon.calls_script,
        motion_duration=constants.INITIAL_MOTION_DURATION,
        motions_count_limit=constants.INITIAL_MOTIONS_COUNT_LIMIT,
        objections_threshold=constants.INITIAL_OBJECTIONS_THRESHOLD,
        tx_params={"from": deployer},
        **optional_roles,
    )


def test_deploy_core_easy_track_contracts(accounts, lido_contracts):
    deployer, admin = accounts[0], accounts[1]
    easy_track, evm_script_executor = deploy(lido_contracts, deployer, admin)

    assert easy_track.governanceToken() == lido_contracts.ldo
    assert easy_track.evmScriptExecutor() == evm_script_executor
    assert easy_track.motionDuration() == constants.INITIAL_MOTION_DURATION
    assert easy_track.motionsCountLimit() == constants.INITIAL_MOTIONS_COUNT_LIMIT
    assert easy_track.objectionsThreshold() == constants.INITIAL_OBJECTIONS_THRESHOLD

    assert evm_script_executor.easyTrack() == easy_track
    assert evm_script_executor.owner() == admin
    assert evm_script_executor.callsScript() == lido_contracts.aragon.calls_script

    assert role_holders(easy_track, accounts[:6]) == {
        "DEFAULT_ADMIN_ROLE": {admin},
        "PAUSE_ROLE": set(),
        "UNPAUSE_ROLE": set(),
        "CANCEL_ROLE": set(),
    }


def test_deploy_core_easy_track_contracts_optional_roles(accounts, lido_contracts):
    deployer, admin, pauser, canceller, additional_admin = accounts[:5]
    easy_track, _ = deploy(
        lido_contracts, deployer, admin, pauser=pauser, canceller=canceller, additional_admin=additional_admin
    )

    assert role_holders(easy_track, accounts[:6]) == {
        "DEFAULT_ADMIN_ROLE": {admin, additional_admin},
        "PAUSE_ROLE": {pauser},
        "UNPAUSE_ROLE": set(),
        "CANCEL_ROLE": {canceller},
    }


def test_deploy_core_easy_track_contracts_rejects_deployer_as_role_holder(accounts, lido_contracts):
    deployer, admin = accounts[0], accounts[1]
    with pytest.raises(AssertionError, match="deployer must not keep any EasyTrack role"):
        deploy(lido_contracts, deployer, admin, pauser=deployer)
