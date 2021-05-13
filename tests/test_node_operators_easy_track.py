import pytest

from brownie.network.state import Chain
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


def test_get_objections_threshold(node_operators_easy_track):
    "Must return correct objections threshold"
    assert node_operators_easy_track.getObjectionsThreshold(
    ) == constants.OBJECTIONS_THRESHOLD


def test_set_objections_threshold_called_by_owner(
    owner,
    node_operators_easy_track
):
    "Must update objections threshold"
    new_objections_threshold = 10_000_000
    assert node_operators_easy_track.getObjectionsThreshold(
    ) == constants.OBJECTIONS_THRESHOLD
    node_operators_easy_track.setObjectionsThreshold(
        new_objections_threshold,
        { 'from': owner }
    )
    assert node_operators_easy_track.getObjectionsThreshold(
    ) == new_objections_threshold


def test_set_objections_threshold_called_not_by_owner(
    node_operators_easy_track
):
    "Must fail with error 'Ownable: caller is not the owner'"
    new_objections_threshold = 10_000_000
    with reverts("Ownable: caller is not the owner"):
        node_operators_easy_track.setObjectionsThreshold(
            new_objections_threshold,
            { 'from': accounts[3] }
        )


def test_create_voting_with_correct_node_operator_id(
    voting_creator,
    node_operators_easy_track
):
    "Must successfully create new voting with correct data"
    chain = Chain()
    node_operator_id = 1
    staking_limit = 1000
    voting_id = node_operators_easy_track.createVoting.call(
        node_operator_id,
        staking_limit,
        { 'from': voting_creator }
    )
    assert voting_id == 1

    node_operators_easy_track.createVoting(
        node_operator_id,
        staking_limit,
        { 'from': voting_creator }
    )

    (
        id,
        duration,
        start_date,
        snapshot_block,
        objections,
        objections_threshold,
        is_enacted,
        is_canceled,
        node_operator_ids,
        staking_limits
    ) = node_operators_easy_track.getVoting(voting_id)
    assert id == 1
    assert duration == constants.VOTING_DURATION
    assert start_date == chain[-1].timestamp
    assert snapshot_block == chain[-1].number
    assert objections == 0
    assert objections_threshold == constants.OBJECTIONS_THRESHOLD
    assert not is_enacted
    assert not is_canceled
    assert node_operator_ids[0] == node_operator_id
    assert staking_limits[0] == staking_limit


def test_create_voting_called_not_by_voting_creator(node_operators_easy_track):
    "Must fail with error 'Caller is not the voting creator'"
    node_operator_id = 1
    staking_limit = 1000
    with reverts("Caller is not the voting creator"):
        node_operators_easy_track.createVoting(
            node_operator_id,
            staking_limit,
            { 'from': accounts[3] }
        )


def test_create_voting_with_not_existed_node_operator(
    voting_creator,
    node_operators_easy_track
):
    "Must fail with error 'NODE_OPERATOR_NOT_FOUND'"
    node_operator_id = 10_000
    staking_limit = 1000
    with reverts("NODE_OPERATOR_NOT_FOUND"):
        node_operators_easy_track.createVoting(
            node_operator_id,
            staking_limit,
            { 'from': voting_creator }
        )


def test_create_voting_with_disabled_node_operator(
    voting_creator,
    node_operators_easy_track
):
    "Must fail with error 'Operator disabled'"
    pass