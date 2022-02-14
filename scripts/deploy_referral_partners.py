from brownie import chain, network

from utils.evm_script import encode_call_script
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
    ReferralPartnersRegistry,
    AddReferralPartner,
    RemoveReferralPartner,
    TopUpReferralPartners
)

def main():
    netname = "goerli" if network_name().split('-')[0] == "goerli" else "mainnet"

    contracts = lido.contracts(network=netname)
    et_contracts = deployed_easy_track.contracts(network=netname)
    deployer = get_deployer_account(get_is_live(), network=netname)

    easy_track = et_contracts.easy_track
    evm_script_executor = et_contracts.evm_script_executor

    # address allowed to create motions to add, remove or top up referral partners
    referral_partners_multisig = get_env("REFERRAL_PARTNERS_MULTISIG")

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", netname, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Governance Token", contracts.ldo)
    log.ok("Aragon Voting", contracts.aragon.voting)
    log.ok("Aragon Finance", contracts.aragon.finance)

    log.br()

    log.nb("Referral Partners Multisig", referral_partners_multisig)
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
        referral_partners_registry,
        add_referral_partner,
        remove_referral_partner,
        top_up_referral_partners
    ) = deploy_referral_partners_contracts(
        evm_script_executor=evm_script_executor,
        lido_contracts=contracts,
        referral_partners_multisig=referral_partners_multisig,
        tx_params=tx_params,
    )

    log.br()

    log.ok("Referral factories have been deployed...")
    log.nb("Deployed ReferralPartnersRegistry", referral_partners_registry)
    log.nb("Deployed AddReferralPartner", add_referral_partner)
    log.nb("Deployed RemoveReferralPartner", remove_referral_partner)
    log.nb("Deployed TopUpReferralPartners", top_up_referral_partners)

    log.br()

    if (get_is_live()):
        log.ok("Trying to verify contracts...")
        ReferralPartnersRegistry.publish_source(referral_partners_registry)
        AddReferralPartner.publish_source(add_referral_partner)
        RemoveReferralPartner.publish_source(remove_referral_partner)
        TopUpReferralPartners.publish_source(top_up_referral_partners)

    log.br()

    if easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer):
        log.ok("Easy Track is under deployer control")
        log.ok("Finalize deploy by adding factories to Easy Track?")

        if not prompt_bool():
            log.nb("Aborting")
            return

        deployment.add_evm_script_referral_partners_factories(
            easy_track=easy_track,
            add_referral_partner=add_referral_partner,
            remove_referral_partner=remove_referral_partner,
            top_up_referral_partners=top_up_referral_partners,
            referral_partners_registry=referral_partners_registry,
            lido_contracts=contracts
        )
    elif easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), contracts.aragon.voting):
        log.ok("Easy Track is under DAO Voting control")
        log.ok("To finalize deploy, please create voting that adds factories to Easy Track")
    else:
        raise Exception("Bad permissions setup")

    print("Hit <Enter> to quit script")
    input()


def deploy_referral_partners_contracts(
    evm_script_executor,
    lido_contracts,
    referral_partners_multisig,
    tx_params,
):
    referral_partners_registry = deployment.deploy_referral_partners_registry(
        voting=lido_contracts.aragon.voting,
        evm_script_executor=evm_script_executor,
        tx_params=tx_params,
    )
    add_referral_partner = deployment.deploy_add_referral_partner(
        referral_partners_registry=referral_partners_registry,
        referral_partners_multisig=referral_partners_multisig,
        tx_params=tx_params,
    )
    remove_referral_partner = deployment.deploy_remove_referral_partner(
        referral_partners_registry=referral_partners_registry,
        referral_partners_multisig=referral_partners_multisig,
        tx_params=tx_params,
    )
    top_up_referral_partners = deployment.deploy_top_up_referral_partners(
        finance=lido_contracts.aragon.finance,
        governance_token=lido_contracts.ldo,
        referral_partners_registry=referral_partners_registry,
        referral_partners_multisig=referral_partners_multisig,
        tx_params=tx_params,
    )

    return (
        referral_partners_registry,
        add_referral_partner,
        remove_referral_partner,
        top_up_referral_partners
    )
