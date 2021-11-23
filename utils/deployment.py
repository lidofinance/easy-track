from brownie import (
    EasyTrack,
    TopUpLegoProgram,
    EVMScriptExecutor,
    AddRewardProgram,
    RemoveRewardProgram,
    TopUpRewardPrograms,
    RewardProgramsRegistry,
    IncreaseNodeOperatorStakingLimit,
)


def deploy_easy_track(
    admin,
    governance_token,
    motion_duration,
    motions_count_limit,
    objections_threshold,
    tx_params,
):
    return EasyTrack.deploy(
        governance_token,
        admin,
        motion_duration,
        motions_count_limit,
        objections_threshold,
        tx_params,
    )


def deploy_evm_script_executor(
    aragon_voting, easy_track, aragon_calls_script, tx_params
):
    evm_script_executor = EVMScriptExecutor.deploy(
        aragon_calls_script, easy_track, tx_params
    )
    evm_script_executor.transferOwnership(aragon_voting, tx_params)
    easy_track.setEVMScriptExecutor(evm_script_executor, tx_params)
    return evm_script_executor


def deploy_reward_programs_registry(voting, evm_script_executor, tx_params):
    return RewardProgramsRegistry.deploy(
        voting, [voting, evm_script_executor], [voting, evm_script_executor], tx_params
    )


def deploy_increase_node_operator_staking_limit(node_operators_registry, tx_params):
    return IncreaseNodeOperatorStakingLimit.deploy(node_operators_registry, tx_params)


def deploy_top_up_lego_program(
    finance, lego_program, lego_committee_multisig, tx_params
):
    return TopUpLegoProgram.deploy(
        lego_committee_multisig, finance, lego_program, tx_params
    )


def deploy_add_reward_program(
    reward_programs_registry, reward_programs_multisig, tx_params
):
    return AddRewardProgram.deploy(
        reward_programs_multisig, reward_programs_registry, tx_params
    )


def deploy_remove_reward_program(
    reward_programs_registry, reward_programs_multisig, tx_params
):
    return RemoveRewardProgram.deploy(
        reward_programs_multisig, reward_programs_registry, tx_params
    )


def deploy_top_up_reward_programs(
    finance,
    governance_token,
    reward_programs_registry,
    reward_programs_multisig,
    tx_params,
):
    return TopUpRewardPrograms.deploy(
        reward_programs_multisig,
        reward_programs_registry,
        finance,
        governance_token,
        tx_params,
    )


def deploy_reward_programs_registry(voting, evm_script_executor, tx_params):
    return RewardProgramsRegistry.deploy(
        voting, [voting, evm_script_executor], [voting, evm_script_executor], tx_params
    )


def grant_roles(easy_track, admin, pause_address, tx_params):
    easy_track.grantRole(easy_track.PAUSE_ROLE(), admin, tx_params)
    easy_track.grantRole(easy_track.UNPAUSE_ROLE(), admin, tx_params)
    easy_track.grantRole(easy_track.CANCEL_ROLE(), admin, tx_params)
    easy_track.grantRole(easy_track.PAUSE_ROLE(), pause_address, tx_params)


def add_evm_script_factories(
    easy_track,
    add_reward_program,
    top_up_lego_program,
    remove_reward_program,
    top_up_reward_programs,
    reward_programs_registry,
    increase_node_operator_staking_limit,
    lido_contracts,
    tx_params,
):
    easy_track.addEVMScriptFactory(
        increase_node_operator_staking_limit,
        create_permission(
            lido_contracts.node_operators_registry, "setNodeOperatorStakingLimit"
        ),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        top_up_lego_program,
        create_permission(lido_contracts.aragon.finance, "newImmediatePayment"),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        top_up_reward_programs,
        create_permission(lido_contracts.aragon.finance, "newImmediatePayment"),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        add_reward_program,
        create_permission(reward_programs_registry, "addRewardProgram"),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        remove_reward_program,
        create_permission(reward_programs_registry, "removeRewardProgram"),
        tx_params,
    )


def transfer_admin_role(deployer, easy_track, new_admin, tx_params):
    easy_track.grantRole(easy_track.DEFAULT_ADMIN_ROLE(), new_admin, tx_params)
    easy_track.revokeRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer, tx_params)


def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]
