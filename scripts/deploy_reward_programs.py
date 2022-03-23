from brownie import chain, network

from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    prompt_bool,
    network_name
)
from utils import (
    deployment,
    lido,
    deployed_easy_track,
    log
)

from brownie import (
    RewardProgramsRegistry,
    AddRewardProgram,
    RemoveRewardProgram,
    TopUpRewardPrograms
)

def main():
    netname = "goerli" if network_name().split('-')[0] == "goerli" else "mainnet"

    contracts = lido.contracts(network=netname)
    et_contracts = deployed_easy_track.contracts(network=netname)
    deployer = get_deployer_account(get_is_live(), network=netname)

    easy_track = et_contracts.easy_track
    evm_script_executor = et_contracts.evm_script_executor

    # address allowed to create motions to add, remove or top up reward programs
    reward_programs_multisig = get_env("REWARD_PROGRAMS_MULTISIG")

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", netname, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Governance Token", contracts.ldo)
    log.ok("Aragon Voting", contracts.aragon.voting)
    log.ok("Aragon Finance", contracts.aragon.finance)

    log.br()

    log.nb("Reward Programs Multisig", reward_programs_multisig)
    log.nb("Deployed EasyTrack", easy_track)
    log.nb("Deployed EVMScript Executor", evm_script_executor)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = { "from": deployer }
    if (get_is_live()):
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "300 gwei"

    (
        reward_programs_registry,
        add_reward_program,
        remove_reward_program,
        top_up_reward_programs
    ) = deploy_reward_programs_contracts(
        evm_script_executor=evm_script_executor,
        lido_contracts=contracts,
        reward_programs_multisig=reward_programs_multisig,
        tx_params=tx_params,
    )

    log.br()

    log.ok("Reward programs factories have been deployed...")
    log.nb("Deployed RewardProgramsRegistry", reward_programs_registry)
    log.nb("Deployed AddRewardProgram", add_reward_program)
    log.nb("Deployed RemoveRewardProgram", remove_reward_program)
    log.nb("Deployed TopUpRewardPrograms", top_up_reward_programs)

    log.br()

    if (get_is_live() and get_env("FORCE_VERIFY", False)):
        log.ok("Trying to verify contracts...")
        RewardProgramsRegistry.publish_source(reward_programs_registry)
        AddRewardProgram.publish_source(add_reward_program)
        RemoveRewardProgram.publish_source(remove_reward_program)
        TopUpRewardPrograms.publish_source(top_up_reward_programs)

    log.br()

    if easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer):
        log.ok("Easy Track is under deployer control")
        log.ok("Finalize deploy by adding factories to Easy Track?")

        if not prompt_bool():
            log.nb("Aborting")
            return

        deployment.add_evm_script_reward_programs_factories(
            easy_track=easy_track,
            add_reward_program=add_reward_program,
            remove_reward_program=remove_reward_program,
            top_up_reward_programs=top_up_reward_programs,
            reward_programs_registry=reward_programs_registry,
            lido_contracts=contracts
        )
    elif easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), contracts.aragon.voting):
        log.ok("Easy Track is under DAO Voting control")
        log.ok("To finalize deploy, please create voting that adds factories to Easy Track")
    else:
        log.ok("Easy Track is under another account's control")
        log.ok("To finalize deploy, please manually add factories to Easy Track")

    print("Hit <Enter> to quit script")
    input()


def deploy_reward_programs_contracts(
    evm_script_executor,
    lido_contracts,
    reward_programs_multisig,
    tx_params,
):
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
        reward_programs_registry=reward_programs_registry,
        reward_programs_multisig=reward_programs_multisig,
        tx_params=tx_params,
    )

    return (
        reward_programs_registry,
        add_reward_program,
        remove_reward_program,
        top_up_reward_programs
    )
