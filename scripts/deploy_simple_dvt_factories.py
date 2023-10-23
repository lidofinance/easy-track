from brownie import chain

from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)
from utils import lido, log
import os

from brownie import (
    AddNodeOperators,
    ActivateNodeOperators,
    DeactivateNodeOperators,
    ChangeNodeOperatorManagers,
    SetNodeOperatorNames,
    SetNodeOperatorRewardAddresses,
    SetVettedValidatorsLimits,
    UpdateTargetValidatorLimits,
    web3,
)


def get_trusted_caller():
    if "TRUSTED_CALLER" not in os.environ:
        raise EnvironmentError("Please set TRUSTED_CALLER env variable")
    trusted_caller = os.environ["TRUSTED_CALLER"]

    assert web3.isAddress(trusted_caller), "Trusted caller address is not valid"

    return trusted_caller


def main():
    network_name = get_network_name()
    contracts = lido.contracts(network=network_name)

    deployer = get_deployer_account(get_is_live(), network=network_name)
    trusted_caller = get_trusted_caller()

    log.br()

    log.nb("Current network", network_name(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("Simple DVT module address", contracts.simple_dvt)
    log.ok("ACL", contracts.aragon.acl)
    log.ok("Trusted caller", trusted_caller)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    log.br()

    add_node_operator_address = AddNodeOperators.deploy(
        trusted_caller, contracts.simple_dvt, contracts.aragon.acl, tx_params
    )
    activate_node_operators_address = ActivateNodeOperators.deploy(
        trusted_caller, contracts.simple_dvt, contracts.aragon.acl, tx_params
    )
    deactivate_node_operators_address = DeactivateNodeOperators.deploy(
        trusted_caller, contracts.simple_dvt, contracts.aragon.acl, tx_params
    )
    set_vetted_validators_limits_address = SetVettedValidatorsLimits.deploy(
        trusted_caller, contracts.simple_dvt, tx_params
    )
    set_node_operator_names_address = SetNodeOperatorNames.deploy(
        trusted_caller, contracts.simple_dvt, tx_params
    )
    set_node_operator_reward_address_address = SetNodeOperatorRewardAddresses.deploy(
        trusted_caller, contracts.simple_dvt, tx_params
    )
    update_tareget_validator_limits_address = UpdateTargetValidatorLimits.deploy(
        trusted_caller, contracts.simple_dvt, tx_params
    )
    change_node_operator_manager_address = ChangeNodeOperatorManagers.deploy(
        trusted_caller, contracts.simple_dvt, contracts.aragon.acl, tx_params
    )

    log.ok("Deployed AddNodeOperators", add_node_operator_address)
    log.ok("Deployed ActivateNodeOperators", activate_node_operators_address)
    log.ok("Deployed DeactivateNodeOperators", deactivate_node_operators_address)
    log.ok("Deployed SetVettedValidatorsLimits", set_vetted_validators_limits_address)
    log.ok("Deployed SetNodeOperatorNames", set_node_operator_names_address)
    log.ok(
        "Deployed SetNodeOperatorRewardAddresses",
        set_node_operator_reward_address_address,
    )
    log.ok(
        "Deployed UpdateTargetValidatorLimits", update_tareget_validator_limits_address
    )
    log.ok("Deployed ChangeNodeOperatorManagers", change_node_operator_manager_address)

    log.br()
    log.nb("All factories have been deployed. Starting code verification")
    log.br()

    AddNodeOperators.publish_source(add_node_operator_address)
    ActivateNodeOperators.publish_source(activate_node_operators_address)
    DeactivateNodeOperators.publish_source(deactivate_node_operators_address)
    SetVettedValidatorsLimits.publish_source(set_vetted_validators_limits_address)
    SetNodeOperatorNames.publish_source(set_node_operator_names_address)
    SetNodeOperatorRewardAddresses.publish_source(
        set_node_operator_reward_address_address
    )
    UpdateTargetValidatorLimits.publish_source(update_tareget_validator_limits_address)
    ChangeNodeOperatorManagers.publish_source(change_node_operator_manager_address)

    log.br()
