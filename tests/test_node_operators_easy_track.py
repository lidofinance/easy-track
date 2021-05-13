import pytest

from brownie import NodeOperatorsEasyTrack, accounts


def test_deploy_node_operators_easy_track():
    "Must deploy NodeOperatorsEasyTrack contract with correct params"
    owner = accounts[0]
    voting_creator = accounts[1]
    contract = owner.deploy(NodeOperatorsEasyTrack, voting_creator)

    assert contract.getVotingCreator() == voting_creator
    assert contract.owner() == owner
