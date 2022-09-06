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
    WhitelistedRecipientsRegistry,
    AddWhitelistedRecipient,
    RemoveWhitelistedRecipient,
    TopUpWhitelistedRecipients
)

def main():
    netname = "goerli" if network_name().split('-')[0] == "goerli" else "mainnet"

    contracts = lido.contracts(network=netname)
    et_contracts = deployed_easy_track.contracts(network=netname)
    deployer = get_deployer_account(get_is_live(), network=netname)

    easy_track = et_contracts.easy_track
    evm_script_executor = et_contracts.evm_script_executor

    # address allowed to create motions to add, remove or top up whitelisted recipients
    whitelisted_recipients_multisig = get_env("WHITELISTED_RECIPIENTS_MULTISIG")

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", netname, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Governance Token", contracts.ldo)
    log.ok("Aragon Voting", contracts.aragon.voting)
    log.ok("Aragon Finance", contracts.aragon.finance)

    log.br()

    log.nb("Whitelisted Recipients Multisig", whitelisted_recipients_multisig)
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
        whitelisted_recipients_registry,
        add_whitelisted_recipient,
        remove_whitelisted_recipient,
        top_up_whitelisted_recipients
    ) = deploy_whitelisted_recipients_contracts(
        evm_script_executor=evm_script_executor,
        lido_contracts=contracts,
        whitelisted_recipients_multisig=whitelisted_recipients_multisig,
        easy_track=easy_track,
        tx_params=tx_params,
    )

    log.br()

    log.ok("Whitelisted recipients factories have been deployed...")
    log.nb("Deployed WhitelistedRecipientsRegistry", whitelisted_recipients_registry)
    log.nb("Deployed AddWhitelistedRecipient", add_whitelisted_recipient)
    log.nb("Deployed RemoveWhitelistedRecipient", remove_whitelisted_recipient)
    log.nb("Deployed TopUpWhitelistedRecipients", top_up_whitelisted_recipients)

    log.br()

    if (get_is_live() and get_env("FORCE_VERIFY", False)):
        log.ok("Trying to verify contracts...")
        WhitelistedRecipientsRegistry.publish_source(whitelisted_recipients_registry)
        AddWhitelistedRecipient.publish_source(add_whitelisted_recipient)
        RemoveWhitelistedRecipient.publish_source(remove_whitelisted_recipient)
        TopUpWhitelistedRecipients.publish_source(top_up_whitelisted_recipients)

    log.br()

    if easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer):
        log.ok("Easy Track is under deployer control")
        log.ok("Finalize deploy by adding factories to Easy Track?")

        if not prompt_bool():
            log.nb("Aborting")
            return

        deployment.add_evm_script_whitelisted_recipients_factories(
            easy_track=easy_track,
            add_whitelisted_recipient=add_whitelisted_recipient,
            remove_whitelisted_recipient=remove_whitelisted_recipient,
            top_up_whitelisted_recipients=top_up_whitelisted_recipients,
            whitelisted_recipients_registry=whitelisted_recipients_registry,
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


def deploy_whitelisted_recipients_contracts(
    evm_script_executor,
    lido_contracts,
    whitelisted_recipients_multisig,
    easy_track,
    tx_params,
):
    whitelisted_recipients_registry = deployment.deploy_whitelisted_recipients_registry(
        voting=lido_contracts.aragon.voting,
        evm_script_executor=evm_script_executor,
        easy_track=easy_track,
        tx_params=tx_params,
    )
    add_whitelisted_recipient = deployment.deploy_add_whitelisted_recipient(
        whitelisted_recipients_registry=whitelisted_recipients_registry,
        whitelisted_recipients_multisig=whitelisted_recipients_multisig,
        tx_params=tx_params,
    )
    remove_whitelisted_recipient = deployment.deploy_remove_whitelisted_recipient(
        whitelisted_recipients_registry=whitelisted_recipients_registry,
        whitelisted_recipients_multisig=whitelisted_recipients_multisig,
        tx_params=tx_params,
    )
    top_up_whitelisted_recipients = deployment.deploy_top_up_whitelisted_recipients(
        finance=lido_contracts.aragon.finance,
        governance_token=lido_contracts.ldo,
        whitelisted_recipients_registry=whitelisted_recipients_registry,
        whitelisted_recipients_multisig=whitelisted_recipients_multisig,
        tx_params=tx_params,
    )

    return (
        whitelisted_recipients_registry,
        add_whitelisted_recipient,
        remove_whitelisted_recipient,
        top_up_whitelisted_recipients
    )
