from brownie import (
    ZERO_ADDRESS,
    accounts,
    interface,
    Contract,
    EasyTrack,
    ContractProxy,
    TopUpLegoProgram,
    EVMScriptExecutor,
    AddRewardProgram,
    TopUpRewardPrograms,
    RemoveRewardProgram,
    RewardProgramsRegistry,
    IncreaseNodeOperatorStakingLimit,
)
from utils.config import get_env, get_is_live, get_deployer_account, prompt_bool


def main():
    deployer = get_deployer_account(get_is_live())
    governance_token = get_env("GOVERNANCE_TOKEN")
    aragon_voting = get_env("ARAGON_VOTING")
    aragon_finance = get_env("ARAGON_FINANCE")
    aragon_calls_script = get_env("ARAGON_CALLS_SCRIPT")
    node_operators_registry = get_env("NODE_OPERATORS_REGISTRY")
    lego_program_vault = get_env("LEGO_PROGRAM_VAULT")
    lego_committee_multisig = get_env("LEGO_COMMITTEE_MULTISIG")
    reward_programs_multisig = get_env("REWARD_PROGRAMS_MULTISIG")

    print(f"Deployer: {deployer}")
    print(f"Governance Token: {governance_token}")
    print(f"Aragon Voting: {aragon_finance}")
    print(f"Aragon Finance: {aragon_voting}")
    print(f"Aragon CallsScript: {aragon_calls_script}")
    print(f"LEGO Program Vault: {lego_program_vault}")
    print(f"LEGO Committee Multisig: {lego_committee_multisig}")
    print(f"Reward Programs Multisig: {reward_programs_multisig}")

    print("Proceed? [y/n]: ")

    if not prompt_bool():
        print("Aborting")
        return

    easy_track = deploy_easy_track_with_proxy(deployer, governance_token)
    evm_script_executor = deploy_evm_script_executor(
        deployer, easy_track, aragon_calls_script, aragon_voting
    )

    deploy_increase_node_operator_staking_limit(
        deployer=deployer,
        easy_track=easy_track,
        node_operators_registry=interface.NodeOperatorsRegistry(
            node_operators_registry
        ),
    )

    deploy_top_up_lego_program(
        deployer=deployer,
        easy_track=easy_track,
        finance=interface.IFinance(aragon_finance),
        lego_program=lego_program_vault,
        lego_committee_multisig=lego_committee_multisig,
    )

    deploy_reward_programs_evm_script_factories(
        deployer=deployer,
        easy_track=easy_track,
        evm_script_executor=evm_script_executor,
        finance=interface.IFinance(aragon_finance),
        governance_token=governance_token,
        reward_programs_multisig=reward_programs_multisig,
    )

    transfer_admin_role(deployer, easy_track, aragon_voting)


def deploy_easy_track_with_proxy(
    deployer,
    governance_token,
):
    easy_track_logic = deployer.deploy(EasyTrack)
    proxy = deployer.deploy(
        ContractProxy,
        easy_track_logic,
        easy_track_logic.__EasyTrackStorage_init.encode_input(
            governance_token, deployer
        ),
    )
    return Contract.from_abi("EasyTrack", proxy.address, EasyTrack.abi)


def deploy_evm_script_executor(
    deployer, easy_track, aragon_calls_script, aragon_voting
):
    evm_script_executor = deployer.deploy(
        EVMScriptExecutor, aragon_calls_script, easy_track, aragon_voting
    )
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": deployer})
    return evm_script_executor


def deploy_reward_programs_registry(deployer, evm_script_executor):
    return deployer.deploy(RewardProgramsRegistry, evm_script_executor)


def deploy_increase_node_operator_staking_limit(
    deployer, easy_track, node_operators_registry
):
    increase_node_operators_staking_limit = deployer.deploy(
        IncreaseNodeOperatorStakingLimit,
        node_operators_registry,
    )
    easy_track.addEVMScriptFactory(
        increase_node_operators_staking_limit,
        create_permission(node_operators_registry, "setNodeOperatorStakingLimit"),
        {"from": deployer},
    )
    return increase_node_operators_staking_limit


def deploy_top_up_lego_program(
    deployer, easy_track, finance, lego_program, lego_committee_multisig
):
    top_up_lego_program = deployer.deploy(
        TopUpLegoProgram, lego_committee_multisig, finance, lego_program
    )
    easy_track.addEVMScriptFactory(
        top_up_lego_program,
        create_permission(finance, "newImmediatePayment"),
        {"from": deployer},
    )
    return top_up_lego_program


def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]


def deploy_reward_programs_evm_script_factories(
    deployer,
    easy_track,
    evm_script_executor,
    finance,
    governance_token,
    reward_programs_multisig,
):
    reward_programs_registry = deployer.deploy(
        RewardProgramsRegistry, evm_script_executor
    )

    add_reward_program = deployer.deploy(
        AddRewardProgram, reward_programs_multisig, reward_programs_registry
    )
    easy_track.addEVMScriptFactory(
        add_reward_program,
        create_permission(reward_programs_registry, "addRewardProgram"),
        {"from": deployer},
    )

    remove_reward_program = deployer.deploy(
        RemoveRewardProgram, reward_programs_multisig, reward_programs_registry
    )
    easy_track.addEVMScriptFactory(
        remove_reward_program,
        create_permission(reward_programs_registry, "removeRewardProgram"),
        {"from": deployer},
    )

    top_up_reward_programs = deployer.deploy(
        TopUpRewardPrograms,
        reward_programs_multisig,
        reward_programs_registry,
        finance,
        governance_token,
    )
    easy_track.addEVMScriptFactory(
        top_up_reward_programs,
        create_permission(finance, "newImmediatePayment"),
        {"from": deployer},
    )


def transfer_admin_role(deployer, easy_track, new_admin):
    easy_track.grantRole(easy_track.DEFAULT_ADMIN_ROLE(), new_admin, {"from": deployer})
    easy_track.revokeRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer, {"from": deployer})
