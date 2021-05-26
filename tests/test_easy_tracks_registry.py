import pytest

from brownie import EasyTracksRegistry, accounts, reverts

import constants


def test_deploy_easy_tracks_registry():
    "Must deploy EasyTracksRegistry contract with correct params"
    owner = accounts[0]
    contract = owner.deploy(EasyTracksRegistry, constants.ARAGON_AGENT)

    assert contract.motionDuration() == constants.DEFAULT_MOTION_DURATION
    assert contract.objectionsThreshold(
    ) == constants.DEFAULT_OBJECTIONS_THRESHOLD
    assert contract.aragonAgent() == constants.ARAGON_AGENT


def test_set_motion_duration_called_by_owner(
    owner,
    easy_tracks_registry,
):
    "Must update motion duration when value is greater or equal than MIN_MOTION_DURATION"
    new_motion_duration = 64 * 60 * 60
    assert easy_tracks_registry.motionDuration(
    ) == constants.DEFAULT_MOTION_DURATION
    easy_tracks_registry.setMotionDuration(new_motion_duration,
                                           {'from': owner})
    assert easy_tracks_registry.motionDuration() == new_motion_duration


def test_set_motion_duration_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_motion_duration = 64 * 60 * 60
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.setMotionDuration(new_motion_duration,
                                               {'from': stranger})


def test_set_motion_duration_called_with_small_value(
    owner,
    easy_tracks_registry,
):
    "Must fail with error 'VALUE_TOO_SMALL'"
    new_motion_duration = 32 * 60 * 60
    with reverts("VALUE_TOO_SMALL"):
        easy_tracks_registry.setMotionDuration(new_motion_duration,
                                               {'from': owner})