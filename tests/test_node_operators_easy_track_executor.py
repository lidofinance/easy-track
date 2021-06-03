from brownie import NodeOperatorsEasyTrackExecutor, reverts, accounts
from eth_abi import encode_single

import constants
from utils.evm_script import encode_call_script


def test_deploy(owner, easy_tracks_registry):
    "Must deploy contract with correct params"
    executor = owner.deploy(
        NodeOperatorsEasyTrackExecutor,
        easy_tracks_registry,
        constants.NODE_OPERATORS_REGISTRY,
    )
    assert executor.easyTracksRegistry() == easy_tracks_registry
    assert executor.nodeOperatorsRegistry() == constants.NODE_OPERATORS_REGISTRY


def test_before_create_motion_guard_called_by_stranger(
    stranger, node_operators_easy_track_executor
):
    "Must fail with error: 'NOT_EASYTRACK_REGISTRY'"
    with reverts("NOT_EASYTRACK_REGISTRY"):
        node_operators_easy_track_executor.beforeCreateMotionGuard(
            stranger, "0x", {"from": stranger}
        )


def test_before_create_motion_guard_node_operator_not_found(
    owner,
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error: 'NODE_OPERATOR_NOT_FOUND'"
    node_operator = accounts[4]
    node_operators_registry_stub.setActive(False)
    node_operators_registry_stub.setId(1)

    with reverts("NODE_OPERATOR_NOT_FOUND"):
        node_operators_easy_track_executor.beforeCreateMotionGuard(
            node_operator,
            encode_single("(uint256,uint256)", [2, 200]),
            {"from": easy_tracks_registry},
        )


def test_before_create_motion_guard_node_operator_disabled(
    owner,
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error: 'NODE_OPERATOR_DISABLED'"
    node_operator = accounts[4]
    node_operators_registry_stub.setActive(False)
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setRewardAddress(node_operator)

    with reverts("NODE_OPERATOR_DISABLED"):
        node_operators_easy_track_executor.beforeCreateMotionGuard(
            node_operator,
            encode_single("(uint256,uint256)", [1, 200]),
            {"from": easy_tracks_registry},
        )


def test_before_create_motion_guard_different_reward_address(
    owner,
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error: 'CALLER_IS_NOT_NODE_OPERATOR'"
    node_operator = accounts[4]
    node_operators_registry_stub.setActive(True)
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setRewardAddress(node_operator)

    with reverts("CALLER_IS_NOT_NODE_OPERATOR"):
        node_operators_easy_track_executor.beforeCreateMotionGuard(
            accounts[5],
            encode_single("(uint256,uint256)", [1, 200]),
            {"from": easy_tracks_registry},
        )


def test_before_create_motion_guard_new_staking_limit_less_than_current(
    owner,
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error: 'STAKING_LIMIT_TOO_LOW'"
    node_operator = accounts[4]
    node_operators_registry_stub.setActive(True)
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setRewardAddress(node_operator)
    node_operators_registry_stub.setStakingLimit(300)
    node_operators_registry_stub.setTotalSigningKeys(1000)

    with reverts("STAKING_LIMIT_TOO_LOW"):
        node_operators_easy_track_executor.beforeCreateMotionGuard(
            node_operator,
            encode_single("(uint256,uint256)", [1, 200]),
            {"from": easy_tracks_registry},
        )


def test_before_create_motion_guard_new_staking_limit_less_than_total_signing_keys(
    owner,
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error: 'NOT_ENOUGH_SIGNING_KEYS'"
    node_operator = accounts[4]
    node_operators_registry_stub.setActive(True)
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setRewardAddress(node_operator)
    node_operators_registry_stub.setStakingLimit(300)
    node_operators_registry_stub.setTotalSigningKeys(400)

    with reverts("NOT_ENOUGH_SIGNING_KEYS"):
        node_operators_easy_track_executor.beforeCreateMotionGuard(
            node_operator,
            encode_single("(uint256,uint256)", [1, 500]),
            {"from": easy_tracks_registry},
        )


def test_before_cancel_motion_guard_node_operator_not_found(
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error 'NODE_OPERATOR_NOT_FOUND'"
    node_operator = accounts[4]
    node_operators_registry_stub.setId(1)
    with reverts("NODE_OPERATOR_NOT_FOUND"):
        node_operators_easy_track_executor.beforeCancelMotionGuard(
            node_operator,
            encode_single("(uint256,uint256)", [2, 500]),
            encode_single("uint256", 2),
            {"from": easy_tracks_registry},
        )


def test_before_cancel_motion_guard_different_reward_address(
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error 'CALLER_IS_NOT_NODE_OPERATOR'"
    node_operator = accounts[4]
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setRewardAddress(node_operator)

    with reverts("CALLER_IS_NOT_NODE_OPERATOR"):
        node_operators_easy_track_executor.beforeCancelMotionGuard(
            accounts[5],
            encode_single("(uint256,uint256)", [1, 500]),
            encode_single("uint256", 1),
            {"from": easy_tracks_registry},
        )


def test_execute_node_operator_not_found(
    easy_tracks_registry,
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error 'NODE_OPERATOR_NOT_FOUND'"
    node_operators_registry_stub.setId(1)

    with reverts("NODE_OPERATOR_NOT_FOUND"):
        node_operators_easy_track_executor.execute(
            encode_single("(uint256,uint256)", [2, 500]),
            "0x",
        )


def test_execute_node_operator_node_operator_disabled(
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error 'NODE_OPERATOR_DISABLED'"
    node_operators_registry_stub.setActive(False)
    node_operators_registry_stub.setId(1)

    with reverts("NODE_OPERATOR_DISABLED"):
        node_operators_easy_track_executor.execute(
            encode_single("(uint256,uint256)", [1, 200]), "0x"
        )


def test_execute_new_staking_limit_less_than_current(
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error: 'STAKING_LIMIT_TOO_LOW'"
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setActive(True)
    node_operators_registry_stub.setStakingLimit(300)
    node_operators_registry_stub.setTotalSigningKeys(1000)

    with reverts("STAKING_LIMIT_TOO_LOW"):
        node_operators_easy_track_executor.execute(
            encode_single("(uint256,uint256)", [1, 200]), "0x"
        )


def test_execute_new_staking_limit_less_than_total_signing_keys(
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must fail with error: 'NOT_ENOUGH_SIGNING_KEYS'"
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setActive(True)
    node_operators_registry_stub.setStakingLimit(300)
    node_operators_registry_stub.setTotalSigningKeys(400)

    with reverts("NOT_ENOUGH_SIGNING_KEYS"):
        node_operators_easy_track_executor.execute(
            encode_single("(uint256,uint256)", [1, 500]), "0x"
        )


def test_execute(
    node_operators_registry_stub,
    node_operators_easy_track_executor,
):
    "Must return correct evmScript to set new staking limit for node operator"
    node_operators_registry_stub.setId(1)
    node_operators_registry_stub.setActive(True)
    node_operators_registry_stub.setStakingLimit(300)
    node_operators_registry_stub.setTotalSigningKeys(400)

    evm_script = node_operators_easy_track_executor.execute(
        encode_single("(uint256,uint256)", [1, 350]), "0x"
    )

    assert evm_script == encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    1, 350
                ),
            )
        ]
    )
