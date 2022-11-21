from brownie import chain, network

from utils.config import (
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
    AllowedRecipientsBuilder
)

def main():
    network_name = get_network_name()

    if (not (network_name == "goerli" or network_name == "goerli-fork")):
        raise EnvironmentError("network is not supported")

    trusted_caller = "0x3eaE0B337413407FB3C65324735D797ddc7E071D"
    token = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    limit = 10_000 * 1e18
    period = 1
    spent_amount = 0

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)
    deployer = get_deployer_account(get_is_live(), network=network_name)

    easy_track = et_contracts.easy_track
    evm_script_executor = et_contracts.evm_script_executor

    allowed_recipients_builder = AllowedRecipientsBuilder.at("0x1082512D1d60a0480445353eb55de451D261b684")

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", network_name, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)

    log.ok("Token", contracts.ldo)
    log.ok("Trusted caller", trusted_caller)
    log.ok("Limit", limit)
    log.ok("Period", period)
    log.ok("Spent amount", spent_amount)
    
    log.ok("Aragon Finance", contracts.aragon.finance)
    log.ok("Aragon Agent", contracts.aragon.agent)
    log.ok("EasyTrack", easy_track)
    log.ok("EVMScript Executor", evm_script_executor)

    log.br()

    print("Proceed? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = { 
        "from": deployer,
        "priority_fee": "2 gwei",
        "max_fee": "50 gwei"
    }

    tx = allowed_recipients_builder.deploySingleRecipientTopUpOnlySetup(
        trusted_caller,
        'Trusted multisig',
        token,
        limit,
        period,
        spent_amount,
        tx_params
    )

    registryAddress = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    topUpAddress = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]


    log.ok("Allowed recipients easy track contracts have been deployed...")
    log.nb("Deployed AllowedRecipientsRegistryDeployed", registryAddress)
    log.nb("Deployed TopUpAllowedRecipientsDeployed", topUpAddress)

    log.br()
