from brownie import chain, network
from utils.config import get_env, get_is_live, get_deployer_account, prompt_bool
from utils import deployment, lido
from utils.constants import (
    INITIAL_MOTION_DURATION,
    INITIAL_MOTIONS_COUNT_LIMIT,
    INITIAL_OBJECTIONS_THRESHOLD,
)


def main():
    contracts = lido.contracts()
    deployer = get_deployer_account(get_is_live())

    # address of Lido's LEGO program
    lego_program_vault = get_env("LEGO_PROGRAM_VAULT")
    # address allowed to create motions to top up LEGO program
    lego_committee_multisig = get_env("LEGO_COMMITTEE_MULTISIG")
    # address allowed to create motions to add, remove or top up reward program
    reward_programs_multisig = get_env("REWARD_PROGRAMS_MULTISIG")
    # address to grant PAUSE_ROLE (optional)
    pause_address = get_env("PAUSE_ADDRESS")

    print(f"Current network: {network.show_active()} (chain id: {chain.id})")
    print(f"Deployer: {deployer}")
    print(f"Governance Token: {contracts.ldo}")
    print(f"Motion Duration: {INITIAL_MOTION_DURATION} seconds")
    print(f"Motions Count Limit: {INITIAL_MOTIONS_COUNT_LIMIT}")
    print(f"Objections Threshold: {INITIAL_OBJECTIONS_THRESHOLD}")
    print(f"Aragon Voting: {contracts.aragon.voting}")
    print(f"Aragon Finance: {contracts.aragon.finance}")
    print(f"Aragon CallsScript: {contracts.aragon.calls_script}")
    print(f"Node Operators Registry: {contracts.node_operators_registry}")
    print(f"LEGO Program Vault: {lego_program_vault}")
    print(f"LEGO Committee Multisig: {lego_committee_multisig}")
    print(f"Reward Programs Multisig: {reward_programs_multisig}")
    print(f"Pause address: {pause_address}")

    print("Proceed? [y/n]: ")

    if not prompt_bool():
        print("Aborting")
        return

    tx_params = {
        "from": deployer,
        "gas_price": "100 gwei"
        # "priority_fee": "4 gwei",
    }

    deploy_easy_tracks(
        lido_contracts=contracts,
        lego_program_vault=lego_program_vault,
        lego_committee_multisig=lego_committee_multisig,
        reward_programs_multisig=reward_programs_multisig,
        pause_address=pause_address,
        tx_params=tx_params,
    )


def deploy_easy_tracks(
    lido_contracts,
    lego_program_vault,
    lego_committee_multisig,
    reward_programs_multisig,
    pause_address,
    tx_params,
):
    easy_track = deployment.deploy_easy_track(
        admin=tx_params["from"],
        governance_token=lido_contracts.ldo,
        motion_duration=INITIAL_MOTION_DURATION,
        motions_count_limit=INITIAL_MOTIONS_COUNT_LIMIT,
        objections_threshold=INITIAL_OBJECTIONS_THRESHOLD,
        tx_params=tx_params,
    )
    evm_script_executor = deployment.deploy_evm_script_executor(
        aragon_voting=lido_contracts.aragon.voting,
        easy_track=easy_track,
        aragon_calls_script=lido_contracts.aragon.calls_script,
        tx_params=tx_params,
    )
    increase_node_operators_staking_limit = (
        deployment.deploy_increase_node_operator_staking_limit(
            node_operators_registry=lido_contracts.node_operators_registry,
            tx_params=tx_params,
        )
    )
    top_up_lego_program = deployment.deploy_top_up_lego_program(
        finance=lido_contracts.aragon.finance,
        lego_program=lego_program_vault,
        lego_committee_multisig=lego_committee_multisig,
        tx_params=tx_params,
    )
    reward_programs_registry = deployment.deploy_reward_programs_registry(
        voting=lido_contracts.aragon.voting,
        evm_script_executor=evm_script_executor,
        tx_params=tx_params,
    )
    add_reward_program = deployment.deploy_add_reward_program(
        reward_programs_registry=reward_programs_registry,
        reward_programs_multisig=reward_programs_multisig,
        tx_params=tx_params,
    )
    remove_reward_program = deployment.deploy_remove_reward_program(
        reward_programs_registry=reward_programs_registry,
        reward_programs_multisig=reward_programs_multisig,
        tx_params=tx_params,
    )
    top_up_reward_programs = deployment.deploy_top_up_reward_programs(
        finance=lido_contracts.aragon.finance,
        governance_token=lido_contracts.ldo,
        reward_programs_multisig=reward_programs_multisig,
        reward_programs_registry=reward_programs_registry,
        tx_params=tx_params,
    )

    deployment.add_evm_script_factories(
        easy_track=easy_track,
        add_reward_program=add_reward_program,
        top_up_lego_program=top_up_lego_program,
        remove_reward_program=remove_reward_program,
        top_up_reward_programs=top_up_reward_programs,
        reward_programs_registry=reward_programs_registry,
        increase_node_operator_staking_limit=increase_node_operators_staking_limit,
        lido_contracts=lido_contracts,
        tx_params=tx_params,
    )

    deployment.grant_roles(
        easy_track=easy_track,
        admin=lido_contracts.aragon.voting,
        pause_address=pause_address,
        tx_params=tx_params,
    )

    deployment.transfer_admin_role(
        deployer=tx_params["from"],
        easy_track=easy_track,
        new_admin=lido_contracts.aragon.voting,
        tx_params=tx_params,
    )
    return (
        easy_track,
        evm_script_executor,
        increase_node_operators_staking_limit,
        top_up_lego_program,
        reward_programs_registry,
        add_reward_program,
        remove_reward_program,
        top_up_reward_programs,
    )
