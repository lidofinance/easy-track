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
    log,
    deployed_date_time
)

from brownie import (
    AllowedRecipientsFactory,
    AllowedRecipientsBuilder
)

def main():
    network_name = get_network_name()
    deployer = get_deployer_account(get_is_live(), network=network_name)

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Governance Token", contracts.ldo)
    log.ok("Aragon Finance", contracts.aragon.finance)
    log.ok("Aragon Agent", contracts.aragon.agent)

    log.br()

    log.nb("Deployed EasyTrack", et_contracts.easy_track)
    log.nb("Deployed EVMScript Executor", et_contracts.evm_script_executor)

    log.br()

    tx_params = { 
        "from": deployer,
        "priority_fee": "2 gwei",
        "max_fee": "50 gwei"
    }