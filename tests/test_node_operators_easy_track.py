import pytest

from brownie import NodeOperatorsEasyTrack, accounts, reverts
import constants


def test_deploy_node_operators_easy_track():
    "Must deploy NodeOperatorsEasyTrack contract with correct params"
    owner = accounts[0]
    voting_creator = accounts[1]
    contract = owner.deploy(
        NodeOperatorsEasyTrack,
        voting_creator,
        constants.VOTING_DURATION,
        constants.OBJECTIONS_THRESHOLD
    )

    assert contract.getVotingCreator() == voting_creator
    assert contract.owner() == owner


def test_get_voting_creator(voting_creator, node_operators_easy_track):
    "Must return correct voting creator address"
    assert node_operators_easy_track.getVotingCreator() == voting_creator


def test_set_voting_creator_called_by_owner(
    owner,
    voting_creator,
    node_operators_easy_track
):
    "Must set new voting creator address"
    new_voting_creator = accounts[2]
    assert node_operators_easy_track.getVotingCreator() == voting_creator
    node_operators_easy_track.setVotingCreator(
        new_voting_creator,
        { 'from': owner }
    )
    assert node_operators_easy_track.getVotingCreator() == new_voting_creator


def test_set_voting_creator_called_not_by_owner(node_operators_easy_track):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_voting_creator = accounts[2]
    with reverts("Ownable: caller is not the owner"):
        node_operators_easy_track.setVotingCreator(
            new_voting_creator,
            { 'from': accounts[3] }
        )


def test_get_voting_duration(node_operators_easy_track):
    "Must return corret voting duration"
    assert node_operators_easy_track.getVotingDuration(
    ) == constants.VOTING_DURATION


def test_set_voting_duration_called_by_owner(owner, node_operators_easy_track):
    "Must update voting duration"
    new_voting_duration = 48 * 60 * 60
    assert node_operators_easy_track.getVotingDuration(
    ) == constants.VOTING_DURATION
    node_operators_easy_track.setVotingDuration(
        new_voting_duration,
        { 'from': owner }
    )
    assert node_operators_easy_track.getVotingDuration() == new_voting_duration


def test_set_voting_duration_called_not_by_owner(
    accounts,
    node_operators_easy_track
):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_voting_duration = 48 * 60 * 60
    with reverts("Ownable: caller is not the owner"):
        node_operators_easy_track.setVotingDuration(
            new_voting_duration,
            { 'from': accounts[3] }
        )