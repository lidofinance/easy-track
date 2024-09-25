import brownie
from scripts.deploy import deploy_easy_tracks
from utils import lido, constants, deployment


def test_deploy_script(accounts):
    deployer = accounts[0]
    lego_program_vault = accounts[1]
    lego_committee_multisig = accounts[2]
    reward_programs_multisig = accounts[3]
    pause_address = accounts[4]
    lido_contracts = lido.contracts(network=brownie.network.show_active())
    (
        easy_track,
        evm_script_executor,
        increase_node_operators_staking_limit,
        top_up_lego_program,
        reward_programs_registry,
        add_reward_program,
        remove_reward_program,
        top_up_reward_programs,
    ) = deploy_easy_tracks(
        lido_contracts=lido_contracts,
        lego_program_vault=lego_program_vault,
        lego_committee_multisig=lego_committee_multisig,
        reward_programs_multisig=reward_programs_multisig,
        pause_address=pause_address,
        tx_params={"from": deployer},
    )
    assert easy_track.governanceToken() == lido_contracts.ldo
    assert easy_track.evmScriptExecutor() == evm_script_executor
    assert easy_track.motionDuration() == constants.INITIAL_MOTION_DURATION
    assert easy_track.motionsCountLimit() == constants.INITIAL_MOTIONS_COUNT_LIMIT
    assert easy_track.objectionsThreshold() == constants.INITIAL_OBJECTIONS_THRESHOLD
    assert easy_track.hasRole(easy_track.PAUSE_ROLE(), lido_contracts.aragon.voting)
    assert easy_track.hasRole(easy_track.CANCEL_ROLE(), lido_contracts.aragon.voting)
    assert easy_track.hasRole(easy_track.UNPAUSE_ROLE(), lido_contracts.aragon.voting)
    assert easy_track.hasRole(
        easy_track.DEFAULT_ADMIN_ROLE(), lido_contracts.aragon.voting
    )
    assert not easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer)

    assert evm_script_executor.callsScript() == lido_contracts.aragon.calls_script
    assert evm_script_executor.easyTrack() == easy_track
    assert evm_script_executor.owner() == lido_contracts.aragon.voting

    assert (
        increase_node_operators_staking_limit.nodeOperatorsRegistry()
        == lido_contracts.node_operators_registry
    )

    assert top_up_lego_program.finance() == lido_contracts.aragon.finance
    assert top_up_lego_program.legoProgram() == lego_program_vault
    assert top_up_lego_program.trustedCaller() == lego_committee_multisig

    assert reward_programs_registry.hasRole(
        reward_programs_registry.DEFAULT_ADMIN_ROLE(), lido_contracts.aragon.voting
    )
    assert reward_programs_registry.hasRole(
        reward_programs_registry.ADD_REWARD_PROGRAM_ROLE(), evm_script_executor
    )
    assert reward_programs_registry.hasRole(
        reward_programs_registry.ADD_REWARD_PROGRAM_ROLE(), lido_contracts.aragon.voting
    )
    assert reward_programs_registry.hasRole(
        reward_programs_registry.REMOVE_REWARD_PROGRAM_ROLE(), evm_script_executor
    )
    assert reward_programs_registry.hasRole(
        reward_programs_registry.REMOVE_REWARD_PROGRAM_ROLE(),
        lido_contracts.aragon.voting,
    )

    assert add_reward_program.trustedCaller() == reward_programs_multisig
    assert add_reward_program.rewardProgramsRegistry() == reward_programs_registry

    assert remove_reward_program.trustedCaller() == reward_programs_multisig
    assert remove_reward_program.rewardProgramsRegistry() == reward_programs_registry

    assert top_up_reward_programs.trustedCaller() == reward_programs_multisig
    assert top_up_reward_programs.finance() == lido_contracts.aragon.finance
    assert top_up_reward_programs.rewardToken() == lido_contracts.ldo
    assert top_up_reward_programs.rewardProgramsRegistry() == reward_programs_registry

    # validate evm script factories permissions
    set_node_operator_staking_limit_permission = (
        lido_contracts.node_operators_registry.address
        + lido_contracts.node_operators_registry.setNodeOperatorStakingLimit.signature[
            2:
        ]
    )
    new_immediate_payment_permission = (
        lido_contracts.aragon.finance.address
        + lido_contracts.aragon.finance.newImmediatePayment.signature[2:]
    )
    add_reward_program_permission = (
        reward_programs_registry.address
        + reward_programs_registry.addRewardProgram.signature[2:]
    )
    remove_reward_program_permission = (
        reward_programs_registry.address
        + reward_programs_registry.removeRewardProgram.signature[2:]
    )
    assert (
        easy_track.evmScriptFactoryPermissions(increase_node_operators_staking_limit)
        == set_node_operator_staking_limit_permission
    )
    assert (
        easy_track.evmScriptFactoryPermissions(top_up_lego_program)
        == new_immediate_payment_permission
    )
    assert (
        easy_track.evmScriptFactoryPermissions(add_reward_program)
        == add_reward_program_permission
    )
    assert (
        easy_track.evmScriptFactoryPermissions(remove_reward_program)
        == remove_reward_program_permission
    )
    assert (
        easy_track.evmScriptFactoryPermissions(top_up_reward_programs)
        == new_immediate_payment_permission
    )
