import time

from typing import (Dict, Tuple, Optional)

from brownie import chain, network
from brownie.network.transaction import TransactionReceipt

from utils.vote_for_new_factories import (
    FactoryToAdd,
    FactoryToRemove,
    create_voting_on_new_factories
)

from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    network_name
)

from utils import (
    lido,
    deployed_easy_track,
    log
)

def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]

def start_vote(
    netname: str,
    deployer: Optional[str]
) -> int:
    contracts = lido.contracts(network=netname)
    et_contracts = deployed_easy_track.contracts(network=netname)

    tx_params = { "from": deployer }
    if (get_is_live()):
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "300 gwei"

    easy_track = et_contracts.easy_track

    prog_type = get_env("REWARD_PROGRAMS_TYPE")
    reward_programs = None
    if prog_type == "reward_programs":
        reward_programs = et_contracts.reward_programs
    elif prog_type == "referral_partners":
        reward_programs = et_contracts.referral_partners
    else:
        raise Exception(f"Unknown REWARD_PROGRAMS_TYPE: {prog_type}")

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", netname, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Reward programs type", prog_type)
    log.ok("Aragon Voting", contracts.aragon.voting)
    log.ok("Aragon Finance", contracts.aragon.finance)

    log.br()

    log.nb("Deployed EasyTrack", easy_track)
    log.nb("Deployed RewardProgramsRegistry", reward_programs.reward_programs_registry)
    log.nb("Deployed AddRewardProgram", reward_programs.add_reward_program)
    log.nb("Deployed RemoveRewardProgram", reward_programs.remove_reward_program)
    log.nb("Deployed TopUpRewardPrograms", reward_programs.top_up_reward_programs)

    log.br()

    factories_to_remove = [
        # Use if need to replace some factories
        # FactoryToRemove(factory=...)
    ]

    factories_to_add = [
        FactoryToAdd(
            factory=reward_programs.add_reward_program,
            permissions=create_permission(
                reward_programs.reward_programs_registry,
                "addRewardProgram"
            )
        ),
        FactoryToAdd(
            factory=reward_programs.top_up_reward_programs,
            permissions=create_permission(
                contracts.aragon.finance,
                "newImmediatePayment")
            ),
        FactoryToAdd(
            factory=reward_programs.remove_reward_program,
            permissions=create_permission(
                reward_programs.reward_programs_registry,
                "removeRewardProgram"
            )
        )
    ]

    vote_id = create_voting_on_new_factories(
        easy_track=easy_track,
        factories_to_remove=factories_to_remove,
        factories_to_add=factories_to_add,
        network=netname,
        tx_params=tx_params
    )

    return vote_id

def main():
    netname = "goerli" if network_name().split('-')[0] == "goerli" else "mainnet"
    deployer = get_deployer_account(get_is_live(), network=netname)

    vote_id = start_vote(netname, deployer)

    vote_id >= 0 and print(f'Vote successfully started! Vote id: {vote_id}.')

    print("Hit <Enter> to quit script")
    input()
