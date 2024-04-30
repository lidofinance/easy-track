import pytest

from scripts.vote_for_reward_programs import start_vote

from utils import lido, deployed_easy_track

from utils.config import get_network_name, get_deployer_account, get_is_live

factories_to_remove_with_vote = [
    # Intentionally left empty
]

factories_to_add_with_vote = [
    "0x929547490Ceb6AeEdD7d72F1Ab8957c0210b6E51",
    "0xE9eb838fb3A288bF59E9275Ccd7e124fDff88a9C",
    "0x54058ee0E0c87Ad813C002262cD75B98A7F59218",
]

ldo_vote_executors_for_tests = {
    "mainnet": [
        "0x3e40d73eb977dc6a537af587d48316fee66e9c8c",
        "0xb8d83908aab38a159f3da47a59d84db8e1838712",
        "0xa2dfc431297aee387c05beef507e5335e684fbcd",
    ],
    "goerli": [
        "0xa5f1d7d49f581136cf6e58b32cbe9a2039c48ba1",
        "0x4333218072d5d7008546737786663c38b4d561a4",
        "0xfda7e01b2718c511bf016030010572e833c7ae6a",
    ],
}


@pytest.mark.skip(reason="already deployed om mainnet")
def test_vote_for_reward_programs(helpers, accounts, vote_id_from_env):
    network_name = get_network_name()

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    easy_track = et_contracts.easy_track
    factories_before = easy_track.getEVMScriptFactories()

    for f in factories_to_remove_with_vote:
        assert f in factories_before

    for f in factories_to_add_with_vote:
        assert f not in factories_before

    ##
    ## START VOTE
    ##
    deployer = get_deployer_account(get_is_live(), network=network_name)
    vote_id = vote_id_from_env or start_vote(network_name, deployer)

    _ = helpers.execute_vote(
        vote_id=vote_id,
        accounts=accounts,
        dao_voting=contracts.aragon.voting,
        ldo_vote_executors_for_tests=ldo_vote_executors_for_tests[network_name],
    )

    factories_after = easy_track.getEVMScriptFactories()

    for f in factories_to_remove_with_vote:
        assert f not in factories_after

    for f in factories_to_add_with_vote:
        assert f in factories_after

    assert len(factories_after) - len(factories_before) == len(factories_to_add_with_vote) - len(
        factories_to_remove_with_vote
    )
