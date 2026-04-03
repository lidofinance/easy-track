"""
Grant Easy Track executor permissions on devnet.
Handles different ACL managers: direct grantPermission for Voting-managed,
and Agent.forward for Agent-managed permissions.
"""
import os
import time
from brownie import accounts, interface, network
from utils import lido
from utils.evm_script import encode_call_script


def main():
    deployer = accounts.add(os.environ["DEPLOYER_PRIVATE_KEY"])
    evm_script_executor = os.environ["EVM_SCRIPT_EXECUTOR"]

    net = network.show_active()
    lido_contracts = lido.contracts(network=net)
    acl = lido_contracts.aragon.acl
    voting = lido_contracts.aragon.voting
    agent = lido_contracts.aragon.agent
    token_manager = lido_contracts.aragon.token_manager

    nor = lido_contracts.node_operators_registry
    finance = lido_contracts.aragon.finance

    # Roles
    SET_LIMIT_ROLE = nor.SET_NODE_OPERATOR_LIMIT_ROLE()
    CREATE_PAYMENTS_ROLE = finance.CREATE_PAYMENTS_ROLE()

    tx_params = {"from": deployer, "priority_fee": "2 gwei"}

    # Check current state
    has_set_limit = acl.hasPermission(evm_script_executor, nor.address, SET_LIMIT_ROLE)
    has_create_payments = acl.hasPermission(evm_script_executor, finance.address, CREATE_PAYMENTS_ROLE)

    print(f"Deployer: {deployer.address}")
    print(f"EVMScriptExecutor: {evm_script_executor}")
    print(f"Has SET_NODE_OPERATOR_LIMIT_ROLE: {has_set_limit}")
    print(f"Has CREATE_PAYMENTS_ROLE: {has_create_payments}")

    if has_set_limit and has_create_payments:
        print("All permissions already granted!")
        return

    # Build EVM script for permissions that need granting
    calls = []

    # Finance CREATE_PAYMENTS_ROLE — manager is Voting, so direct grantPermission works
    if not has_create_payments:
        print(f"Will grant CREATE_PAYMENTS_ROLE on Finance (manager=Voting)")
        calls.append((
            acl.address,
            acl.grantPermission.encode_input(evm_script_executor, finance.address, CREATE_PAYMENTS_ROLE),
        ))

    # NOR SET_NODE_OPERATOR_LIMIT_ROLE — manager is Agent
    # Need to wrap in Agent.forward() call, which Voting can call
    if not has_set_limit:
        print(f"Will grant SET_NODE_OPERATOR_LIMIT_ROLE on NOR (manager=Agent, via Agent.forward)")
        # Encode the ACL grant call
        acl_grant_call = acl.grantPermission.encode_input(evm_script_executor, nor.address, SET_LIMIT_ROLE)
        # Wrap in Agent forward (EVM script format for Agent)
        agent_forward_script = encode_call_script([(acl.address, acl_grant_call)])
        # Agent.forward() call
        calls.append((
            agent.address,
            agent.forward.encode_input(agent_forward_script),
        ))

    evm_script = encode_call_script(calls)

    print(f"\nCreating vote with {len(calls)} permission grants...")
    voting_tx = token_manager.forward(
        encode_call_script([(
            voting.address,
            voting.newVote.encode_input(evm_script, "Grant Easy Track executor permissions"),
        )]),
        tx_params,
    )

    vote_id = voting_tx.events["StartVote"]["voteId"]
    print(f"Vote created: {vote_id}")

    # Vote
    if voting.canVote(vote_id, deployer.address):
        print("Voting...")
        voting.vote(vote_id, True, False, tx_params)
        print("Voted!")

    # Wait for vote to pass
    vote_time = voting.voteTime()
    print(f"Waiting {vote_time}s for vote to pass...")
    time.sleep(vote_time + 10)

    # Execute
    if voting.canExecute(vote_id):
        print("Executing vote...")
        voting.executeVote(vote_id, tx_params)
        print(f"Vote {vote_id} executed!")
    else:
        print(f"Vote {vote_id} cannot be executed yet!")
        return

    # Verify
    print("\nVerifying permissions...")
    assert acl.hasPermission(evm_script_executor, nor.address, SET_LIMIT_ROLE), "SET_NODE_OPERATOR_LIMIT_ROLE not granted!"
    assert acl.hasPermission(evm_script_executor, finance.address, CREATE_PAYMENTS_ROLE), "CREATE_PAYMENTS_ROLE not granted!"
    print("All permissions granted and verified!")
