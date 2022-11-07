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

    if (not (network_name == "goerli" or network_name == "goerli-fork")):
        raise EnvironmentError("network is not supported")

    recipients = [
        "0xbbe8dDEf5BF31b71Ff5DbE89635f9dB4DeFC667E",
        "0x07fC01f46dC1348d7Ce43787b5Bbd52d8711a92D",
        "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1",
        "0xDDFFac49946D1F6CE4d9CaF3B9C7d340d4848A1C",
        "0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97"
    ]

    titles = [
        'recipient 1',
        'recipient 2',
        'recipient 3',
        'recipient 4',
        'recipient 5',
    ]

    trusted_caller = "0xc0e1418de75cD11B4C5cF60B9F86713e80689517"

    limit = 10_000 * 1e18
    period = 1
    spent_amount = 0

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)
    deployer = get_deployer_account(get_is_live(), network=network_name)

    easy_track = et_contracts.easy_track
    evm_script_executor = et_contracts.evm_script_executor

    allowed_recipients_builder = AllowedRecipientsBuilder.at("0x6fC826e3544C179D5D58AeaE9A1d6159Cd515Aaf")

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

    tx = allowed_recipients_builder.deployFullSetup(
        trusted_caller,
        contracts.ldo, 
        limit, 
        period,
        recipients, 
        titles,
        spent_amount,
        tx_params
    )

    regestryAddress = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    topUpAddress = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
    addRecipientAddress = tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
    removeAllowedRecipientAddress = tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]


    log.ok("Allowed recipients easy track contracts have been deployed...")
    log.nb("Deployed AllowedRecipientsRegistryDeployed", regestryAddress)
    log.nb("Deployed TopUpAllowedRecipientsDeployed", topUpAddress)
    log.nb("Deployed AddAllowedRecipientDeployed", addRecipientAddress)
    log.nb("Deployed RemoveAllowedRecipientDeployed", removeAllowedRecipientAddress)

    log.br()
