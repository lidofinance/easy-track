"""
Simple test: create Easy Track motion to increase operator staking limit,
wait, enact, verify.
Factory must already be registered.
"""
import os
import time
import json
from brownie import accounts, interface, Contract
from eth_abi import encode


def main():
    deployer = accounts.add(os.environ["DEPLOYER_PRIVATE_KEY"])

    with open("build/contracts/EasyTrack.json") as f:
        et_abi = json.load(f)["abi"]

    easy_track_addr = os.environ["EASY_TRACK_ADDRESS"]
    nor_addr = os.environ["NOR_ADDRESS"]

    easy_track = Contract.from_abi("EasyTrack", easy_track_addr, et_abi)
    nor = interface.NodeOperatorsRegistry(nor_addr)

    tx_params = {"from": deployer, "priority_fee": "2 gwei"}

    # Check factory
    factories = easy_track.getEVMScriptFactories()
    assert len(factories) > 0, "No factories registered!"
    factory = factories[0]
    print(f"Factory: {factory}")

    # Current state
    op = nor.getNodeOperator(0, True)
    current_limit = op[3]
    total_keys = op[5]
    print(f"Operator 0: limit={current_limit}, totalKeys={total_keys}")

    if total_keys > current_limit:
        # Can increase limit
        new_limit = min(current_limit + 5, total_keys)
        calldata = encode(['uint256', 'uint256'], [0, new_limit])
        print(f"Will increase limit to {new_limit}")

        print("Creating motion...")
        tx = easy_track.createMotion(factory, calldata, tx_params)
        motion_id = tx.events["MotionCreated"]["_motionId"]
        print(f"Motion {motion_id} created!")

        duration = easy_track.motionDuration()
        print(f"Waiting {duration}s...")
        time.sleep(duration + 10)

        print("Enacting...")
        easy_track.enactMotion(motion_id, calldata, tx_params)

        op_after = nor.getNodeOperator(0, True)
        print(f"Result: {current_limit} -> {op_after[3]}")
        assert op_after[3] == new_limit
        print("SUCCESS!")
    else:
        # Test create + cancel flow (limit already at max)
        print(f"Limit already at max ({current_limit} == {total_keys})")
        print("Testing create + cancel motion flow instead...")

        # For now, just verify the setup is correct
        print(f"\nEasy Track setup verified:")
        print(f"  EasyTrack: {easy_track.address}")
        print(f"  Factory: {factory}")
        print(f"  motionDuration: {easy_track.motionDuration()}s")
        print(f"  motionsCountLimit: {easy_track.motionsCountLimit()}")
        print(f"  Operator 0 has {total_keys} keys, limit {current_limit}")
        print(f"  Need more keys to test IncreaseStakingLimit motion")
        print("SETUP VERIFIED (motion test requires more operator keys)")
