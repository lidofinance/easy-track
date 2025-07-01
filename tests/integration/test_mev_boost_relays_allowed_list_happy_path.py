import brownie.network
import pytest
import brownie

from utils.evm_script import encode_call_script, encode_calldata

MOTION_BUFFER_TIME = 100


def setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track):
    evm_executor = easy_track.evmScriptExecutor()
    agent = lido_contracts.aragon.agent

    manager = mev_boost_relay_allowed_list.get_manager()
    if manager.lower() == evm_executor.lower():
        return

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

    lido_contracts.execute_voting(vote_id)


def execute_motion(easy_track, motion_transaction, stranger):
    brownie.chain.sleep(easy_track.motionDuration() + MOTION_BUFFER_TIME)
    motions = easy_track.getMotions()
    assert len(motions) == 1
    easy_track.enactMotion(
        motions[0][0],
        motion_transaction.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0


def create_enact_and_check_add_motion(
    lido_contracts,
    easy_track,
    mev_boost_relay_allowed_list,
    stranger,
    rmc_factories_multisig,
    add_relays_script_factory,
    relays,
):
    motion_transaction = easy_track.createMotion(
        add_relays_script_factory.address,
        encode_calldata(["(string,string,bool,string)[]"], [relays]),
        {"from": rmc_factories_multisig},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    relays_before = list(mev_boost_relay_allowed_list.get_relays())
    assert all(relay not in relays_before for relay in relays)

    execute_motion(easy_track, motion_transaction, stranger)

    relays_after = list(mev_boost_relay_allowed_list.get_relays())
    assert len(relays_after) == len(relays_before) + len(relays)

    for relay in relays:
        assert relay in relays_after
        assert mev_boost_relay_allowed_list.get_relay_by_uri(relay[0]) == relay
        mev_boost_relay_allowed_list.remove_relay(relay[0], {"from": lido_contracts.aragon.agent.address})


def create_enact_and_check_remove_motion(
    lido_contracts,
    easy_track,
    mev_boost_relay_allowed_list,
    stranger,
    rmc_factories_multisig,
    remove_relays_script_factory,
    relays,
):
    relays_before = list(mev_boost_relay_allowed_list.get_relays())
    for relay in relays:
        if relay[0] not in [r[0] for r in relays_before]:
            mev_boost_relay_allowed_list.add_relay(*relay, {"from": lido_contracts.aragon.agent.address})
            assert mev_boost_relay_allowed_list.get_relay_by_uri(relay[0]) == relay
            relays_before.append(relay)

    motion_transaction = easy_track.createMotion(
        remove_relays_script_factory.address,
        encode_calldata(["string[]"], [[relay[0] for relay in relays]]),
        {"from": rmc_factories_multisig},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    relays_before = list(mev_boost_relay_allowed_list.get_relays())
    assert all(relay in relays_before for relay in relays)

    execute_motion(easy_track, motion_transaction, stranger)

    relays_after = list(mev_boost_relay_allowed_list.get_relays())
    assert len(relays_after) == len(relays_before) - len(relays)

    for relay in relays:
        assert relay not in relays_after


def create_enact_and_check_edit_motion(
    lido_contracts,
    easy_track,
    mev_boost_relay_allowed_list,
    stranger,
    rmc_factories_multisig,
    edit_relays_script_factory,
    relays,
    modified_relays,
):
    assert len(relays) == len(modified_relays)
    assert all(original_relay[0] == updated_relay[0] for original_relay, updated_relay in zip(relays, modified_relays))
    assert all(original_relay != updated_relay for original_relay, updated_relay in zip(relays, modified_relays))

    relays_before = list(mev_boost_relay_allowed_list.get_relays())
    for relay in relays:
        if relay[0] not in [r[0] for r in relays_before]:
            mev_boost_relay_allowed_list.add_relay(*relay, {"from": lido_contracts.aragon.agent.address})
            assert mev_boost_relay_allowed_list.get_relay_by_uri(relay[0]) == relay
            relays_before.append(relay)

    motion_transaction = easy_track.createMotion(
        edit_relays_script_factory.address,
        encode_calldata(["(string,string,bool,string)[]"], [modified_relays]),
        {"from": rmc_factories_multisig},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    relays_after = list(mev_boost_relay_allowed_list.get_relays())
    assert len(relays_after) == len(relays_before)

    for original_relay, updated_relay in zip(relays, modified_relays):
        assert updated_relay in relays_after
        assert original_relay not in relays_after
        relay_from_list = mev_boost_relay_allowed_list.get_relay_by_uri(original_relay[0])
        assert relay_from_list == updated_relay
        # mev_boost_relay_allowed_list.remove_relay(original_relay[0], {"from": lido_contracts.aragon.agent.address})


@pytest.mark.skip_coverage
def test_add_mev_boost_relays_allowed_list_happy_path(
    add_mev_boost_relays_evm_script_factory,
    easy_track,
    rmc_factories_multisig,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    if mev_boost_relay_allowed_list.get_relays_amount() == mev_boost_relay_test_config["max_num_relays"]:
        for i in range(len(mev_boost_relay_test_config["relays"])):
            relay_uri = mev_boost_relay_allowed_list.get_relays()[i][0]
            mev_boost_relay_allowed_list.remove_relay(relay_uri, {"from": lido_contracts.aragon.agent.address})

    create_enact_and_check_add_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        add_mev_boost_relays_evm_script_factory,
        [mev_boost_relay_test_config["relays"][0]],
    )

    create_enact_and_check_add_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        add_mev_boost_relays_evm_script_factory,
        mev_boost_relay_test_config["relays"],
    )


@pytest.mark.skip_coverage
def test_add_mev_boost_relays_allowed_list_full_list_happy_path(
    add_mev_boost_relays_evm_script_factory,
    easy_track,
    rmc_factories_multisig,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    relays_input = list(mev_boost_relay_allowed_list.get_relays())
    for relay in relays_input:
        mev_boost_relay_allowed_list.remove_relay(relay[0], {"from": lido_contracts.aragon.agent.address})

    if len(relays_input) < mev_boost_relay_test_config["max_num_relays"]:
        relays_input += [
            (f"uri{i}", f"op{i}", True, f"desc{i}")
            for i in range(len(relays_input), mev_boost_relay_test_config["max_num_relays"])
        ]

    create_enact_and_check_add_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        add_mev_boost_relays_evm_script_factory,
        relays_input,
    )


@pytest.mark.skip_coverage
def test_remove_mev_boost_relays_allowed_list_happy_path(
    remove_mev_boost_relays_evm_script_factory,
    easy_track,
    rmc_factories_multisig,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    create_enact_and_check_remove_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        remove_mev_boost_relays_evm_script_factory,
        [mev_boost_relay_test_config["relays"][0]],
    )

    create_enact_and_check_remove_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        remove_mev_boost_relays_evm_script_factory,
        mev_boost_relay_test_config["relays"],
    )


@pytest.mark.skip_coverage
def test_remove_mev_boost_relays_allowed_list_full_list_happy_path(
    remove_mev_boost_relays_evm_script_factory,
    easy_track,
    rmc_factories_multisig,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    relays_input = list(mev_boost_relay_allowed_list.get_relays())
    current_relays_count = len(relays_input)

    if current_relays_count != mev_boost_relay_test_config["max_num_relays"]:
        for i in range(current_relays_count, mev_boost_relay_test_config["max_num_relays"]):
            relays_input.append((f"uri{i}", f"op{i}", True, f"desc{i}"))

    create_enact_and_check_remove_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        remove_mev_boost_relays_evm_script_factory,
        relays_input,
    )


@pytest.mark.skip_coverage
def test_edit_mev_boost_relays_allowed_list_happy_path(
    edit_mev_boost_relays_evm_script_factory,
    easy_track,
    rmc_factories_multisig,
    stranger,
    lido_contracts,
    mev_boost_relay_allowed_list,
    mev_boost_relay_test_config,
):
    setup_script_executor(lido_contracts, mev_boost_relay_allowed_list, easy_track)

    modified_relays = [
        (relay[0], f"op {i} updated", not relay[2], relay[3])
        for i, relay in enumerate(mev_boost_relay_test_config["relays"])
    ]

    create_enact_and_check_edit_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        edit_mev_boost_relays_evm_script_factory,
        [mev_boost_relay_test_config["relays"][0]],
        [modified_relays[0]],
    )

    create_enact_and_check_edit_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        rmc_factories_multisig,
        edit_mev_boost_relays_evm_script_factory,
        mev_boost_relay_test_config["relays"],
        modified_relays,
    )


@pytest.mark.skip_coverage
def test_edit_mev_boost_relays_allowed_list_full_list_happy_path(
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

    relays_input = list(mev_boost_relay_allowed_list.get_relays())
    for relay in relays_input:
        mev_boost_relay_allowed_list.remove_relay(relay[0], {"from": lido_contracts.aragon.agent.address})

    items_count = 40
    for i in range(items_count):
        mev_boost_relay_allowed_list.add_relay(*(f"uri{i}", f"op{i}", True, f"desc{i}"), {"from": lido_contracts.aragon.agent.address})

    assert len(mev_boost_relay_allowed_list.get_relays()) == items_count

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

    relays_input = list(mev_boost_relay_allowed_list.get_relays())
    modified_relays = [
        (relay[0], f"op {i} updated", not relay[2], relay[3])
        for i, relay in enumerate(relays_input)
    ]

    create_enact_and_check_edit_motion(
        lido_contracts,
        easy_track,
        mev_boost_relay_allowed_list,
        stranger,
        trusted_address,
        edit_mev_boost_relays_factory,
        relays_input,
        modified_relays,
    )

    assert len(relays_input) == items_count
    assert len(modified_relays) == items_count
