import pytest

from brownie import EasyTracksRegistry, accounts

import constants


def test_deploy_easy_tracks_registry():
    "Must deploy EasyTracksRegistry contract with correct params"
    owner = accounts[0]
    contract = owner.deploy(EasyTracksRegistry, constants.ARAGON_AGENT)

    assert contract.getMotionDuration() == 48 * 60 * 60
    assert contract.getObjectionsThreshold() == 50
    assert contract.getAragonAgent() == constants.ARAGON_AGENT
