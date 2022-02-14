from brownie import chain, network

from utils.vote_for_new_factories import (
    FactoryToAdd, create_voting_on_ref_partners_factories
)

from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    prompt_bool,
    network_name
)

from utils import (
    lido,
    deployed_easy_track,
    log
)

def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]

def main():
    netname = "goerli" if network_name().split('-')[0] == "goerli" else "mainnet"

    contracts = lido.contracts(network=netname)
    et_contracts = deployed_easy_track.contracts(network=netname)
    deployer = get_deployer_account(get_is_live(), network=netname)

    easy_track = et_contracts.easy_track

    log.br()

    log.nb("Current network", network.show_active(), color_hl=log.color_magenta)
    log.nb("Using deployed addresses for", netname, color_hl=log.color_yellow)
    log.ok("chain id", chain.id)
    log.ok("Deployer", deployer)
    log.ok("Aragon Voting", contracts.aragon.voting)
    log.ok("Aragon Finance", contracts.aragon.finance)

    log.br()

    log.nb("Deployed EasyTrack", easy_track)
    log.nb("Deployed ReferralPartnersRegistry", et_contracts.referral_partners_registry)
    log.nb("Deployed AddReferralPartner", et_contracts.add_referral_partner)
    log.nb("Deployed RemoveReferralPartner", et_contracts.remove_referral_partner)
    log.nb("Deployed TopUpReferralPartners", et_contracts.top_up_referral_partners)

    log.br()

    print("Proceed to create vote? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return

    tx_params = { "from": deployer }
    if (get_is_live()):
        tx_params["priority_fee"] = "2 gwei"
        tx_params["max_fee"] = "300 gwei"

    log.br()

    factories = [
        FactoryToAdd(
            factory=et_contracts.add_referral_partner,
            permissions=create_permission(
                et_contracts.referral_partners_registry,
                "addReferralPartner"
            )
        ),
        FactoryToAdd(
            factory=et_contracts.top_up_referral_partners,
            permissions=create_permission(
                contracts.aragon.finance,
                "newImmediatePayment")
            ),
        FactoryToAdd(
            factory=et_contracts.remove_referral_partner,
            permissions=create_permission(
                et_contracts.referral_partners_registry,
                "removeReferralPartner"
            )
        )
    ]

    vote_id = create_voting_on_ref_partners_factories(
        easy_track=easy_track,
        factories=factories,
        network=netname,
        tx_params=tx_params
    )

    print(f"Vote successfully started! Vote id: {vote_id}")

    print("Hit <Enter> to quit script")
    input()
