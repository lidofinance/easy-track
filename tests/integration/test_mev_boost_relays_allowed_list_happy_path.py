import pytest
import brownie

from utils.evm_script import encode_call_script, encode_calldata


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[7]


def setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track):
    evm_executor = easy_track.evmScriptExecutor()
    agent = lido_contracts.aragon.agent

    vote_id, _ = lido_contracts.create_voting(
        evm_script=encode_call_script(
            [
                (
                    agent.address,
                    agent.forward.encode_input(
                        encode_call_script(
                            [
                                (
                                    mev_boost_relay_allowed_list.address,
                                    mev_boost_relay_allowed_list.set_manager.encode_input(evm_executor),
                                )
                            ]
                        ),
                    ),
                )
            ]
        ),
        description="Set manager for MEV Boost Relay Allowed List to EVMScriptExecutor",
        tx_params={"from": agent.address},
    )

    # execute vote
    lido_contracts.execute_voting(vote_id)


# helper function to setup evm script factory
def setup_evm_script_factory(
    factory, permissions, easy_track, trusted_address, voting, deployer, mev_boost_relay_allowed_list
):
    factory = deployer.deploy(factory, trusted_address, mev_boost_relay_allowed_list)
    assert factory.trustedCaller() == trusted_address
    assert factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list

    easy_track.addEVMScriptFactory(factory, permissions, {"from": voting})
    evm_script_factories = easy_track.getEVMScriptFactories()

    assert len(evm_script_factories) == 1
    assert evm_script_factories[0] == factory

    return factory


@pytest.mark.skip_coverage
def test_add_mev_boost_relays_allowed_list_happy_path(
    AddMEVBoostRelays,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    add_relay_permission = mev_boost_relay_allowed_list.address + mev_boost_relay_allowed_list.add_relay.signature[2:]
    add_mev_boost_relays_factory = setup_evm_script_factory(
        AddMEVBoostRelays,
        add_relay_permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        mev_boost_relay_allowed_list,
    )

    def _create_enact_and_check_motion(add_relays_script_factory, relays):
        # create motion to add relays
        tx = easy_track.createMotion(
            add_relays_script_factory.address,
            encode_calldata(
                ["(string,string,bool,string)[]"],
                [relays],
            ),
            {"from": trusted_address},
        )

        motions = easy_track.getMotions()
        assert len(motions) == 1

        # sleep for motion duration
        brownie.chain.sleep(easy_track.motionDuration() + 100)

        # sanity checks
        mev_boost_relay_allowed_list_before = mev_boost_relay_allowed_list.get_relays()
        assert all(relay not in mev_boost_relay_allowed_list_before for relay in relays)

        # enact motion
        easy_track.enactMotion(
            motions[0][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

        assert len(easy_track.getMotions()) == 0

        # check that relays were added to the list with the correct values
        mev_boost_relay_allowed_list_after = mev_boost_relay_allowed_list.get_relays()
        for relay in relays:
            assert relay in mev_boost_relay_allowed_list_after
            assert mev_boost_relay_allowed_list.get_relay_by_uri(relay[0]) == relay

            mev_boost_relay_allowed_list.remove_relay(relay[0], {"from": lido_contracts.aragon.agent.address})

    # single relay setup
    _create_enact_and_check_motion(
        add_mev_boost_relays_factory,
        [mev_boost_relay_test_config["relays"][0]],
    )

    # multiple relays setup
    _create_enact_and_check_motion(
        add_mev_boost_relays_factory,
        mev_boost_relay_test_config["relays"],
    )


@pytest.mark.skip_coverage
def test_remove_mev_boost_relays_allowed_list_happy_path(
    RemoveMEVBoostRelays,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    remove_relay_permission = (
        mev_boost_relay_allowed_list.address + mev_boost_relay_allowed_list.remove_relay.signature[2:]
    )
    remove_mev_boost_relays_factory = setup_evm_script_factory(
        RemoveMEVBoostRelays,
        remove_relay_permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        mev_boost_relay_allowed_list,
    )

    def _create_enact_and_check_motion(remove_relays_script_factory, relays):
        # add relays to the list directly
        for relay in relays:
            mev_boost_relay_allowed_list.add_relay(*relay, {"from": lido_contracts.aragon.agent.address})
            assert mev_boost_relay_allowed_list.get_relay_by_uri(relay[0]) == relay

        # create motion to remove relays
        tx = easy_track.createMotion(
            remove_relays_script_factory.address,
            encode_calldata(
                ["string[]"],
                [[relay[0] for relay in relays]],
            ),
            {"from": trusted_address},
        )

        motions = easy_track.getMotions()
        assert len(motions) == 1

        # sleep for motion duration
        brownie.chain.sleep(easy_track.motionDuration() + 100)

        # sanity checks
        mev_boost_relay_allowed_list_before = mev_boost_relay_allowed_list.get_relays()
        assert all(relay in mev_boost_relay_allowed_list_before for relay in relays)

        # enact motion
        easy_track.enactMotion(
            motions[0][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

        assert len(easy_track.getMotions()) == 0

        # check that relays were removed from the list
        mev_boost_relay_allowed_list_after = mev_boost_relay_allowed_list.get_relays()
        for relay in relays:
            assert relay not in mev_boost_relay_allowed_list_after

    # single relay setup
    _create_enact_and_check_motion(
        remove_mev_boost_relays_factory,
        [mev_boost_relay_test_config["relays"][0]],
    )

    # multiple relays setup
    _create_enact_and_check_motion(
        remove_mev_boost_relays_factory,
        mev_boost_relay_test_config["relays"],
    )


@pytest.mark.skip_coverage
def test_edit_mev_boost_relays_allowed_list_happy_path(
    EditMEVBoostRelays,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    edit_relay_permission = (
        mev_boost_relay_allowed_list.address
        + mev_boost_relay_allowed_list.add_relay.signature[2:]
        + mev_boost_relay_allowed_list.address[2:]
        + mev_boost_relay_allowed_list.remove_relay.signature[2:]
    )
    edit_mev_boost_relays_factory = setup_evm_script_factory(
        EditMEVBoostRelays,
        edit_relay_permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        mev_boost_relay_allowed_list,
    )

    def _create_enact_and_check_motion(edit_relays_script_factory, relays, modified_relays):
        # sanity checks that relays and modified relays have the same length and the same URIs
        assert len(relays) == len(modified_relays)
        assert all(relay[0] == modified_relay[0] for relay, modified_relay in zip(relays, modified_relays))

        # add relays to the list directly
        for relay in relays:
            mev_boost_relay_allowed_list.add_relay(*relay, {"from": lido_contracts.aragon.agent.address})
            assert mev_boost_relay_allowed_list.get_relay_by_uri(relay[0]) == relay

        # create motion to edit relays
        tx = easy_track.createMotion(
            edit_relays_script_factory.address,
            encode_calldata(
                ["(string,string,bool,string)[]"],
                [modified_relays],
            ),
            {"from": trusted_address},
        )

        motions = easy_track.getMotions()
        assert len(motions) == 1

        # sleep for motion duration
        brownie.chain.sleep(easy_track.motionDuration() + 100)

        # enact motion
        easy_track.enactMotion(
            motions[0][0],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

        assert len(easy_track.getMotions()) == 0

        # check that relays were edited in the list
        mev_boost_relay_allowed_list_after = mev_boost_relay_allowed_list.get_relays()

        for relay, new_relay in zip(relays, modified_relays):
            assert new_relay in mev_boost_relay_allowed_list_after
            assert relay not in mev_boost_relay_allowed_list_after

            relay_from_list = mev_boost_relay_allowed_list.get_relay_by_uri(relay[0])
            assert relay_from_list == new_relay
            assert relay_from_list != relay

            # remove relay from the list
            mev_boost_relay_allowed_list.remove_relay(relay[0], {"from": lido_contracts.aragon.agent.address})

    edited_relays = [
        (relay[0], f"op {i}", not relay[2], relay[3]) for i, relay in enumerate(mev_boost_relay_test_config["relays"])
    ]

    # single relay setup
    _create_enact_and_check_motion(
        edit_mev_boost_relays_factory,
        [mev_boost_relay_test_config["relays"][0]],
        [edited_relays[0]],
    )

    # multiple relays setup
    _create_enact_and_check_motion(
        edit_mev_boost_relays_factory,
        mev_boost_relay_test_config["relays"],
        edited_relays,
    )
