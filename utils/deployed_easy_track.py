from typing import Optional
from brownie import (
    EasyTrack,
    EVMScriptExecutor,
    AddRewardProgram,
    RemoveRewardProgram,
    TopUpRewardPrograms,
    RewardProgramsRegistry,
    IncreaseNodeOperatorStakingLimit,
    TopUpLegoProgram,
    Contract
)

def addresses(network="mainnet"):
    if network == "mainnet":
        return EasyTrackSetup(
            easy_track="0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            evm_script_executor="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
            increase_node_operator_staking_limit="0xFeBd8FAC16De88206d4b18764e826AF38546AfE0",
            top_up_lego_program="0x648C8Be548F43eca4e482C0801Ebccccfb944931",
            reward_programs=RewardPrograms(
                add_reward_program="0x9D15032b91d01d5c1D940eb919461426AB0dD4e3",
                remove_reward_program="0xc21e5e72Ffc223f02fC410aAedE3084a63963932",
                top_up_reward_programs="0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7",
                reward_programs_registry="0x3129c041b372ee93a5a8756dc4ec6f154d85bc9a"
            ),
            referral_partners=RewardPrograms(
                add_reward_program=None,
                remove_reward_program=None,
                top_up_reward_programs=None,
                reward_programs_registry=None
            )
        )
    if network == "goerli":
        return EasyTrackSetup(
            easy_track="0xAf072C8D368E4DD4A9d4fF6A76693887d6ae92Af",
            evm_script_executor="0x3c9aca237b838c59612d79198685e7f20c7fe783",
            increase_node_operator_staking_limit="0xE033673D83a8a60500BcE02aBd9007ffAB587714",
            top_up_lego_program="0xb2bcf211F103d7F13789394DD475c2274e044C4C",
            reward_programs=RewardPrograms(
                add_reward_program="0x5560d40b00EA3a64E9431f97B3c79b04e0cdF6F2",
                remove_reward_program="0x31B68d81125E52fE1aDfe4076F8945D1014753b5",
                top_up_reward_programs="0x8180949ac41EF18e844ff8dafE604a195d86Aea9",
                reward_programs_registry="0x28a08f61AE129d0d8BD4380Ae5647e7Add0527ca"
            ),
            referral_partners=RewardPrograms(
                add_reward_program="0xe54ca3e867C52a34d262E94606C7A9371AB820c9",
                remove_reward_program="0x2A0c343087c6cFB721fFa20608A6eD0473C71275",
                top_up_reward_programs="0xB1E898faC74c377bEF16712Ba1CD4738606c19Ee",
                reward_programs_registry="0x4CB0c9987fd670069e4b24c653981E86b261A2ca"
            )
        )
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, goerli."""
    )

def contract_or_none(
    contract: Contract,
    addr: Optional[str]
) -> Optional[Contract]:
    if not addr:
        return None
    return contract.at(addr)


def contracts(network="mainnet"):
    network_addresses = addresses(network)
    return EasyTrackSetup(
        easy_track=contract_or_none(EasyTrack, network_addresses.easy_track),
        evm_script_executor=contract_or_none(EVMScriptExecutor, network_addresses.evm_script_executor),
        increase_node_operator_staking_limit=contract_or_none(
            IncreaseNodeOperatorStakingLimit,
            network_addresses.increase_node_operator_staking_limit
        ),
        top_up_lego_program=contract_or_none(
            TopUpLegoProgram,
            network_addresses.top_up_lego_program
        ),
        reward_programs=RewardPrograms(
            add_reward_program=contract_or_none(
                AddRewardProgram,
                network_addresses.reward_programs.add_reward_program
            ),
            remove_reward_program=contract_or_none(
                RemoveRewardProgram,
                network_addresses.reward_programs.remove_reward_program
            ),
            top_up_reward_programs=contract_or_none(
                TopUpRewardPrograms,
                network_addresses.reward_programs.top_up_reward_programs
            ),
            reward_programs_registry=contract_or_none(
                RewardProgramsRegistry,
                network_addresses.reward_programs.reward_programs_registry
            )
        ),
        referral_partners=RewardPrograms(
            add_reward_program=contract_or_none(
                AddRewardProgram,
                network_addresses.referral_partners.add_reward_program
            ),
            remove_reward_program=contract_or_none(
                RemoveRewardProgram,
                network_addresses.referral_partners.remove_reward_program
            ),
            top_up_reward_programs=contract_or_none(
                TopUpRewardPrograms,
                network_addresses.referral_partners.top_up_reward_programs
            ),
            reward_programs_registry=contract_or_none(
                RewardProgramsRegistry,
                network_addresses.referral_partners.reward_programs_registry
            )
        )
    )

class EasyTrackSetup:
    def __init__(
        self,
        easy_track,
        evm_script_executor,
        increase_node_operator_staking_limit,
        top_up_lego_program,
        reward_programs,
        referral_partners
    ):
        self.easy_track = easy_track
        self.evm_script_executor = evm_script_executor
        self.increase_node_operator_staking_limit = increase_node_operator_staking_limit
        self.top_up_lego_program = top_up_lego_program
        self.reward_programs = reward_programs
        self.referral_partners = referral_partners

class RewardPrograms:
    def __init__(
        self,
        add_reward_program,
        remove_reward_program,
        top_up_reward_programs,
        reward_programs_registry
    ):
        self.add_reward_program = add_reward_program
        self.remove_reward_program = remove_reward_program
        self.top_up_reward_programs = top_up_reward_programs
        self.reward_programs_registry = reward_programs_registry
