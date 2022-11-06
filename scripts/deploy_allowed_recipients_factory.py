from brownie import chain, network

from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)
from utils import (
    lido,
    deployed_easy_track,
    log
)

from brownie import (
    AllowedRecipientsFactory,
    AllowedRecipientsBuilder
)

def main():
    network_name = get_network_name()

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)
    deployer = get_deployer_account(get_is_live(), network=network_name)

    easy_track = et_contracts.easy_track
    evm_script_executor = et_contracts.evm_script_executor

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Governance Token", contracts.ldo)
    log.ok("Aragon Voting", contracts.aragon.voting)
    log.ok("Aragon Finance", contracts.aragon.finance)
    log.ok("Aragon Agent", contracts.aragon.agent)

    log.br()

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
        allowed_recipients_factory,
        allowed_recipients_builder
    ) = deploy_factory_and_builder(
        easy_track = easy_track,
        finance = contracts.aragon.finance,
        agent = contracts.aragon.agent,
        evm_script_executor = evm_script_executor,
        bokky_poo_bahs_date_time_contract,
        tx_params = tx_params,
    )

    log.br()

    log.ok("Allowed recipients factory and builder have been deployed...")
    log.nb("Deployed AllowedRecipientsFactory", allowed_recipients_factory)
    log.nb("Deployed AllowedRecipientsBuilder", allowed_recipients_builder)

    log.br()

    if (get_is_live() and get_env("FORCE_VERIFY", False)):
        log.ok("Trying to verify contracts...")
        AllowedRecipientsFactory.publish_source(allowed_recipients_factory)
        AllowedRecipientsBuilder.publish_source(allowed_recipients_builder)


def deploy_factory_and_builder(
    easy_track,
    finance,
    agent,
    evm_script_executor,
    bokky_poo_bahs_date_time_contract,
    tx_params,
):

    factory = AllowedRecipientsFactory.deploy(
        easy_track,
        finance,
        evm_script_executor,
        agent,
        bokky_poo_bahs_date_time_contract,
        tx_params
    )

    builder = AllowedRecipientsBuilder.deploy(
        factory,
        evm_script_executor,
        agent
    )

    return (
        factory,
        builder
    )
