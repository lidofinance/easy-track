import json
import os

from brownie import (
    chain,
    AddNodeOperators,
    ActivateNodeOperators,
    DeactivateNodeOperators,
    ChangeNodeOperatorManagers,
    SetNodeOperatorNames,
    SetNodeOperatorRewardAddresses,
    SetVettedValidatorsLimits,
    UpdateTargetValidatorLimits,
    IncreaseVettedValidatorsLimit,
    web3,
)

from utils import lido, log
from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
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
    simple_dvt = contracts.simple_dvt.address
    acl = contracts.aragon.acl.address
    lido_address = contracts.steth.address

    log.br()

    log.nb("Current network", network_name, color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.nb("chain id", chain.id)

    log.br()

    log.ok("Deployer", deployer)

    log.br()

    log.ok("Simple DVT module address", simple_dvt)
    log.ok("ACL", acl)
    log.ok("Trusted caller", trusted_caller)
    log.ok("Lido", lido_address)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = {"from": deployer, "priority_fee": "2 gwei", "max_fee": "50 gwei"}

    log.br()

    deployment_artifacts = {}

    # AddNodeOperators
    add_node_operator = AddNodeOperators.deploy(trusted_caller, simple_dvt, acl, lido_address, tx_params)
    deployment_artifacts["AddNodeOperators"] = {
        "contract": "AddNodeOperators",
        "address": add_node_operator.address,
        "constructorArgs": [trusted_caller, simple_dvt, acl, lido_address],
    }

    # ActivateNodeOperators
    activate_node_operators = ActivateNodeOperators.deploy(trusted_caller, simple_dvt, acl, tx_params)
    deployment_artifacts["ActivateNodeOperators"] = {
        "contract": "ActivateNodeOperators",
        "address": activate_node_operators.address,
        "constructorArgs": [trusted_caller, simple_dvt, acl],
    }

    # DeactivateNodeOperators
    deactivate_node_operators = DeactivateNodeOperators.deploy(trusted_caller, simple_dvt, acl, tx_params)
    deployment_artifacts["DeactivateNodeOperators"] = {
        "contract": "DeactivateNodeOperators",
        "address": deactivate_node_operators.address,
        "constructorArgs": [trusted_caller, simple_dvt, acl],
    }

    # SetVettedValidatorsLimits
    set_vetted_validators_limits = SetVettedValidatorsLimits.deploy(trusted_caller, simple_dvt, tx_params)
    deployment_artifacts["SetVettedValidatorsLimits"] = {
        "contract": "SetVettedValidatorsLimits",
        "address": set_vetted_validators_limits.address,
        "constructorArgs": [trusted_caller, simple_dvt],
    }

    # IncreaseVettedValidatorsLimit
    increase_vetted_validators_limits = IncreaseVettedValidatorsLimit.deploy(simple_dvt, tx_params)
    deployment_artifacts["IncreaseVettedValidatorsLimit"] = {
        "contract": "IncreaseVettedValidatorsLimit",
        "address": increase_vetted_validators_limits.address,
        "constructorArgs": [trusted_caller, simple_dvt],
    }

    # SetNodeOperatorNames
    set_node_operator_names = SetNodeOperatorNames.deploy(trusted_caller, simple_dvt, tx_params)
    deployment_artifacts["SetNodeOperatorNames"] = {
        "contract": "SetNodeOperatorNames",
        "address": set_node_operator_names.address,
        "constructorArgs": [trusted_caller, simple_dvt],
    }

    # SetNodeOperatorRewardAddresses
    set_node_operator_reward = SetNodeOperatorRewardAddresses.deploy(
        trusted_caller, simple_dvt, lido_address, tx_params
    )
    deployment_artifacts["SetNodeOperatorRewardAddresses"] = {
        "contract": "SetNodeOperatorRewardAddresses",
        "address": set_node_operator_reward.address,
        "constructorArgs": [trusted_caller, simple_dvt, lido_address],
    }

    # UpdateTargetValidatorLimits
    update_target_validator_limits = UpdateTargetValidatorLimits.deploy(trusted_caller, simple_dvt, tx_params)
    deployment_artifacts["UpdateTargetValidatorLimits"] = {
        "contract": "UpdateTargetValidatorLimits",
        "address": update_target_validator_limits.address,
        "constructorArgs": [trusted_caller, simple_dvt],
    }

    # ChangeNodeOperatorManagers
    change_node_operator_manager = ChangeNodeOperatorManagers.deploy(trusted_caller, simple_dvt, acl, tx_params)
    deployment_artifacts["ChangeNodeOperatorManagers"] = {
        "contract": "ChangeNodeOperatorManagers",
        "address": change_node_operator_manager.address,
        "constructorArgs": [trusted_caller, simple_dvt, acl],
    }

    log.ok("Deployed AddNodeOperators", add_node_operator)
    log.ok("Deployed ActivateNodeOperators", activate_node_operators.address)
    log.ok("Deployed DeactivateNodeOperators", deactivate_node_operators.address)
    log.ok("Deployed SetVettedValidatorsLimits", set_vetted_validators_limits.address)
    log.ok(
        "Deployed IncreaseVettedValidatorsLimit",
        increase_vetted_validators_limits.address,
    )
    log.ok("Deployed SetNodeOperatorNames", set_node_operator_names.address)
    log.ok(
        "Deployed SetNodeOperatorRewardAddresses",
        set_node_operator_reward.address,
    )
    log.ok("Deployed UpdateTargetValidatorLimits", update_target_validator_limits.address)
    log.ok("Deployed ChangeNodeOperatorManagers", change_node_operator_manager.address)

    log.br()
    log.nb("All factories have been deployed.")
    log.nb("Saving artifacts...")

    with open(f"deployed-{network_name}.json", "w") as outfile:
        json.dump(deployment_artifacts, outfile)

    log.nb("Starting code verification.")
    log.br()

    AddNodeOperators.publish_source(add_node_operator)
    ActivateNodeOperators.publish_source(activate_node_operators)
    DeactivateNodeOperators.publish_source(deactivate_node_operators)
    SetVettedValidatorsLimits.publish_source(set_vetted_validators_limits)
    IncreaseVettedValidatorsLimit.publish_source(increase_vetted_validators_limits)
    SetNodeOperatorNames.publish_source(set_node_operator_names)
    SetNodeOperatorRewardAddresses.publish_source(set_node_operator_reward)
    UpdateTargetValidatorLimits.publish_source(update_target_validator_limits)
    ChangeNodeOperatorManagers.publish_source(change_node_operator_manager)

    log.br()
