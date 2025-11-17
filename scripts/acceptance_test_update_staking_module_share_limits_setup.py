from dataclasses import dataclass

from brownie import chain, UpdateStakingModuleShareLimits

from utils import log


@dataclass
class DeployConfig:
    trusted_caller: str
    factory_name: str
    staking_router: str
    staking_module_id: int
    max_stake_share_increase_bp: int
    max_stake_share_decrease_bp: int
    max_priority_share_threshold_increase_bp: int
    max_priority_share_threshold_decrease_bp: int


deploy_config = DeployConfig(
    trusted_caller="",
    factory_name="",
    staking_router="",
    staking_module_id=0,
    max_stake_share_increase_bp=0,
    max_stake_share_decrease_bp=0,
    max_priority_share_threshold_increase_bp=0,
    max_priority_share_threshold_decrease_bp=0,
)


deployment_tx_hash = ""


def main():
    tx = chain.get_transaction(deployment_tx_hash)

    log.br()
    log.nb("tx of creation", deployment_tx_hash)

    log.br()
    log.nb("trusted_caller", deploy_config.trusted_caller)
    log.nb("factory_name", deploy_config.factory_name)
    log.nb("staking_router", deploy_config.staking_router)
    log.nb("staking_module_id", deploy_config.staking_module_id)
    log.nb("max_stake_share_increase_bp", deploy_config.max_stake_share_increase_bp)
    log.nb("max_stake_share_decrease_bp", deploy_config.max_stake_share_decrease_bp)
    log.nb("max_priority_share_threshold_increase_bp", deploy_config.max_priority_share_threshold_increase_bp)
    log.nb("max_priority_share_threshold_decrease_bp", deploy_config.max_priority_share_threshold_decrease_bp)

    log.br()

    factory = UpdateStakingModuleShareLimits.at(tx.contract_address)
    log.nb("UpdateStakingModuleShareLimits address (from tx)", factory)

    log.br()

    assert factory.trustedCaller() == deploy_config.trusted_caller
    log.nb("Trusted caller is correct")

    assert factory.name() == deploy_config.factory_name
    log.nb("Factory name is correct")

    assert factory.stakingRouter() == deploy_config.staking_router
    log.nb("StakingRouter address is correct")

    assert factory.stakingModuleId() == deploy_config.staking_module_id
    log.nb("Staking module id is correct")

    assert factory.maxStakeShareLimitIncrease() == deploy_config.max_stake_share_increase_bp
    assert factory.maxStakeShareLimitDecrease() == deploy_config.max_stake_share_decrease_bp
    log.nb("Stake share deltas are correct")

    assert factory.maxPriorityExitShareThresholdIncrease() == deploy_config.max_priority_share_threshold_increase_bp
    assert factory.maxPriorityExitShareThresholdDecrease() == deploy_config.max_priority_share_threshold_decrease_bp
    log.nb("Priority exit deltas are correct")

    log.br()
