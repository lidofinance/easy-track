from brownie import NodeOperatorsEasyTrack, reverts, accounts
from eth_abi import encode_single

import constants
from utils.evm_script import encode_call_script

MOTION_ID = 2
NODE_OPERATOR_ID = 1
STAKING_LIMIT = 350


# def test_deploy(owner, motions_registry, node_operators_registry):
#     "Must deploy contract with correct params"
#     executor = owner.deploy(
#         NodeOperatorsEasyTrack, motions_registry, node_operators_registry
#     )
#     assert executor.motionsRegistry() == motions_registry
#     assert executor.nodeOperatorsRegistry() == constants.NODE_OPERATORS_REGISTRY


# def test_create_motion_different_reward_address(
#     stranger, node_operator, node_operators_registry_stub, node_operators_easy_track
# ):
#     "Must fail with error: 'CALLER_IS_NOT_NODE_OPERATOR'"

#     with reverts("CALLER_IS_NOT_NODE_OPERATOR"):
#         node_operators_easy_track.createMotion(
#             NODE_OPERATOR_ID, STAKING_LIMIT, {"from": stranger}
#         )


# def test_create_motion_node_operator_disabled(
#     owner, node_operator, node_operators_registry_stub, node_operators_easy_track
# ):
#     "Must fail with error: 'NODE_OPERATOR_DISABLED'"
#     node_operators_registry_stub.setActive(False)

#     with reverts("NODE_OPERATOR_DISABLED"):
#         node_operators_easy_track.createMotion(
#             NODE_OPERATOR_ID, STAKING_LIMIT, {"from": node_operator}
#         )


# def test_create_motion_new_staking_limit_less_than_current(
#     owner, node_operator, node_operators_registry_stub, node_operators_easy_track
# ):
#     "Must fail with error: 'STAKING_LIMIT_TOO_LOW'"

#     with reverts("STAKING_LIMIT_TOO_LOW"):
#         node_operators_easy_track.createMotion(
#             NODE_OPERATOR_ID, 100, {"from": node_operator}
#         )


# def test_create_motion_new_staking_limit_less_than_total_signing_keys(
#     owner, node_operator, node_operators_registry_stub, node_operators_easy_track
# ):
#     "Must fail with error: 'NOT_ENOUGH_SIGNING_KEYS'"

#     with reverts("NOT_ENOUGH_SIGNING_KEYS"):
#         node_operators_easy_track.createMotion(
#             NODE_OPERATOR_ID, 500, {"from": node_operator}
#         )


# def test_create_motion(
#     owner,
#     node_operator,
#     motions_registry_stub,
#     node_operators_easy_track,
#     node_operators_registry_stub,
# ):
#     "Must create new motion with correct data"

#     assert not motions_registry_stub.createMotionCalled()
#     node_operators_easy_track.createMotion(
#         NODE_OPERATOR_ID, STAKING_LIMIT, {"from": node_operator}
#     )
#     assert motions_registry_stub.createMotionCalled()
#     assert motions_registry_stub.motionData() == encode_motion_data(
#         NODE_OPERATOR_ID, STAKING_LIMIT
#     )


# def test_cancel_motion_different_reward_address(
#     stranger, node_operators_registry_stub, node_operators_easy_track
# ):
#     "Must fail with error 'CALLER_IS_NOT_NODE_OPERATOR' if passed"
#     "node operator id has reward address not equal to msg.sender"

#     with reverts("CALLER_IS_NOT_NODE_OPERATOR"):
#         node_operators_easy_track.cancelMotion(
#             MOTION_ID, NODE_OPERATOR_ID, {"from": stranger}
#         )


# def test_cancel_motion(
#     owner,
#     node_operator,
#     node_operators_registry_stub,
#     node_operators_easy_track,
#     motions_registry_stub,
# ):
#     "Must cancel motion if it exists and msg.sender is registered node operator id"

#     node_operators_easy_track.createMotion(
#         NODE_OPERATOR_ID, STAKING_LIMIT, {"from": node_operator}
#     )

#     # cancel motion
#     assert not motions_registry_stub.cancelMotionCalled()
#     node_operators_easy_track.cancelMotion(
#         MOTION_ID, NODE_OPERATOR_ID, {"from": node_operator}
#     )
#     assert motions_registry_stub.cancelMotionCalled()
#     assert motions_registry_stub.cancelMotionId() == MOTION_ID


# def test_enact_motion_node_operator_node_operator_disabled(
#     stranger,
#     node_operators_registry_stub,
#     node_operators_easy_track,
#     motions_registry_stub,
# ):
#     "Must fail with error 'NODE_OPERATOR_DISABLED' if on moment"
#     "of motion enacting node operator was disabled"

#     # simulate that node operator was disabled
#     node_operators_registry_stub.setActive(False)

#     # set motions registry stub data
#     motions_registry_stub.setMotionData(
#         encode_motion_data(NODE_OPERATOR_ID, STAKING_LIMIT)
#     )

#     with reverts("NODE_OPERATOR_DISABLED"):
#         node_operators_easy_track.enactMotion(MOTION_ID, {"from": stranger})


# def test_enact_motion_new_staking_limit_less_than_current(
#     stranger,
#     motions_registry_stub,
#     node_operators_registry_stub,
#     node_operators_easy_track,
# ):
#     "Must fail with error: 'STAKING_LIMIT_TOO_LOW' if on moment"
#     "of motion enacting node operator's staking limit greater than in motion data"

#     # simulate that staking limit for node operator with id 1 was raised
#     node_operators_registry_stub.setStakingLimit(360)

#     # set motions registry stub data
#     motions_registry_stub.setMotionData(
#         encode_motion_data(NODE_OPERATOR_ID, STAKING_LIMIT)
#     )

#     with reverts("STAKING_LIMIT_TOO_LOW"):
#         node_operators_easy_track.enactMotion(MOTION_ID, {"from": stranger})


# def test_enact_motion_new_staking_limit_less_than_total_signing_keys(
#     stranger,
#     motions_registry_stub,
#     node_operators_registry_stub,
#     node_operators_easy_track,
# ):
#     "Must fail with error: 'NOT_ENOUGH_SIGNING_KEYS' if on moment"
#     "of motion enacting node operator's amount of signing keys was lowered"

#     # simulate that total amount of signing keys was lowered for for node operator with id 1
#     node_operators_registry_stub.setTotalSigningKeys(300)

#     # set motions registry stub data
#     motions_registry_stub.setMotionData(
#         encode_motion_data(NODE_OPERATOR_ID, STAKING_LIMIT)
#     )

#     with reverts("NOT_ENOUGH_SIGNING_KEYS"):
#         node_operators_easy_track.enactMotion(MOTION_ID, {"from": stranger})


def test_enact_motion(
    owner,
    stranger,
    node_operator,
    node_operators_registry_stub,
    node_operators_easy_track,
    motions_registry_stub,
):
    "Must enact motion and pass correct evm script to motionsRegistry"

    # set motions registry stub data
    motions_registry_stub.setMotionData(
        encode_motion_data(NODE_OPERATOR_ID, STAKING_LIMIT)
    )

    assert not motions_registry_stub.enactMotionCalled()
    node_operators_easy_track.enactMotion(MOTION_ID, {"from": stranger})
    assert motions_registry_stub.enactMotionCalled()
    assert motions_registry_stub.enactMotionId() == MOTION_ID

    assert motions_registry_stub.evmScript() == encode_call_script(
        [
            (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    NODE_OPERATOR_ID, STAKING_LIMIT
                ),
            )
        ]
    )


def encode_motion_data(node_operator_id, staking_limit):
    return (
        "0x"
        + encode_single("(uint256,uint256)", [node_operator_id, staking_limit]).hex()
    )
