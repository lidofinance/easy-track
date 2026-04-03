"""
Deploy IncreaseNodeOperatorStakingLimit factory, register in EasyTrack,
then test with a motion.
"""
import os
import json
import time
from brownie import accounts, interface, network, Contract, IncreaseNodeOperatorStakingLimit


def main():
    deployer = accounts.add(os.environ["DEPLOYER_PRIVATE_KEY"])

    with open("build/contracts/EasyTrack.json") as f:
        et_abi = json.load(f)["abi"]

    easy_track_addr = os.environ["EASY_TRACK_ADDRESS"]
    nor_addr = os.environ["NOR_ADDRESS"]

    easy_track = Contract.from_abi("EasyTrack", easy_track_addr, et_abi)
    nor = interface.NodeOperatorsRegistry(nor_addr)

    tx_params = {"from": deployer, "priority_fee": "2 gwei"}

    # 1. Deploy IncreaseNodeOperatorStakingLimit factory (or reuse existing)
    existing_factories = easy_track.getEVMScriptFactories()
    if len(existing_factories) > 0:
        print(f"Reusing existing factory: {existing_factories[0]}")
        factory = Contract.from_abi("IncreaseNodeOperatorStakingLimit", existing_factories[0], IncreaseNodeOperatorStakingLimit.abi)
    else:
        # Check if already deployed but not registered (from prev attempt)
        prev_factory = os.environ.get("FACTORY_ADDRESS")
        if prev_factory:
            print(f"Using previously deployed factory: {prev_factory}")
            factory = Contract.from_abi("IncreaseNodeOperatorStakingLimit", prev_factory, IncreaseNodeOperatorStakingLimit.abi)
        else:
            print("Deploying IncreaseNodeOperatorStakingLimit factory...")
            factory = IncreaseNodeOperatorStakingLimit.deploy(nor_addr, tx_params)
            print(f"Factory deployed at: {factory.address}")

    # 2. Register factory in EasyTrack (skip if already registered)
    existing_factories = easy_track.getEVMScriptFactories()
    if factory.address in existing_factories:
        print(f"Factory already registered, skipping vote")
        # Jump to test
        factories = existing_factories
    else:
        admin_role = easy_track.DEFAULT_ADMIN_ROLE()
        has_admin = easy_track.hasRole(admin_role, deployer.address)
        print(f"Deployer has DEFAULT_ADMIN_ROLE: {has_admin}")

    if not has_admin:
        # Need to go through voting to add factory
        # Use Aragon voting
        from utils import lido
        from utils.evm_script import encode_call_script

        net = network.show_active()
        lido_contracts = lido.contracts(network=net)
        voting = lido_contracts.aragon.voting
        token_manager = lido_contracts.aragon.token_manager

        # EasyTrack.addEVMScriptFactory(factory, permissions)
        # permissions = address(20) + methodSelector(4) for each allowed call
        # IncreaseNodeOperatorStakingLimit calls NOR.setNodeOperatorStakingLimit(uint256,uint64)
        from eth_abi import encode as abi_encode
        from eth_utils import keccak
        method_selector = keccak(b"setNodeOperatorStakingLimit(uint256,uint64)")[:4]
        permissions = bytes.fromhex(nor_addr[2:].lower()) + method_selector
        add_factory_call = easy_track.addEVMScriptFactory.encode_input(
            factory.address,
            permissions,
        )

        evm_script = encode_call_script([(easy_track_addr, add_factory_call)])
        voting_script = encode_call_script([(
            voting.address,
            voting.newVote.encode_input(evm_script, "Add IncreaseNodeOperatorStakingLimit factory"),
        )])

        print("Creating vote to register factory...")
        voting_tx = token_manager.forward(voting_script, tx_params)
        vote_id = voting_tx.events["StartVote"]["voteId"]
        print(f"Vote {vote_id} created")

        voting.vote(vote_id, True, False, tx_params)
        print("Voted!")

        vote_time = voting.voteTime()
        print(f"Waiting {vote_time}s...")
        time.sleep(vote_time + 10)

        voting.executeVote(vote_id, tx_params)
        print(f"Vote {vote_id} executed!")
    else:
        # Direct registration
        permissions = bytes.fromhex(nor_addr.lower().replace("0x", "").zfill(40))
        easy_track.addEVMScriptFactory(factory.address, permissions, tx_params)
        print("Factory registered directly!")

    # Verify registration
    factories = easy_track.getEVMScriptFactories()
    print(f"\nRegistered factories: {len(factories)}")
    for f in factories:
        print(f"  {f}")

    assert factory.address in factories, "Factory not registered!"

    # 3. Test motion
    print("\n=== Testing Easy Track Motion ===")
    operator_id = 0
    op = nor.getNodeOperator(operator_id, True)
    current_limit = op[3]
    new_limit = current_limit + 5
    print(f"Operator {operator_id} ({op[1]}): limit {current_limit} -> {new_limit}")

    from eth_abi import encode
    calldata = encode(['uint256', 'uint256'], [operator_id, new_limit])

    print("Creating motion...")
    motion_tx = easy_track.createMotion(factory.address, calldata, tx_params)
    motion_id = motion_tx.events["MotionCreated"]["_motionId"]
    print(f"Motion {motion_id} created!")

    motion_duration = easy_track.motionDuration()
    print(f"Waiting {motion_duration}s for motion duration...")
    time.sleep(motion_duration + 10)

    print("Enacting motion...")
    easy_track.enactMotion(motion_id, calldata, tx_params)
    print(f"Motion {motion_id} enacted!")

    # Verify
    op_after = nor.getNodeOperator(operator_id, True)
    new_actual = op_after[3]
    print(f"\nResult: limit {current_limit} -> {new_actual}")
    assert new_actual == new_limit, f"Expected {new_limit}, got {new_actual}"
    print("\nSUCCESS! Easy Track end-to-end test passed!")
