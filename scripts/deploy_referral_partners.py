from brownie import chain, network
from brownie.utils import color
from utils.config import get_env, get_is_live, get_deployer_account, prompt_bool, network_name
from utils import deployment, lido, deployed_easy_track, log

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
    log.ok("Aragon CallsScript", contracts.aragon.calls_script)
    log.ok("Node Operators Registry", contracts.node_operators_registry)

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

    deploy_referral_partners_contracts(
        easy_track=easy_track,
        evm_script_executor=evm_script_executor,
        lido_contracts=contracts,
        referral_partners_multisig=referral_partners_multisig,
        tx_params=tx_params,
    )

    log.nb("The script execution has been finished, hit <ENTER> to quit ... ")
    input()

def deploy_referral_partners_contracts(
    easy_track,
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

    deployment.add_evm_script_referral_partners_factories(
        easy_track=easy_track,
        add_referral_partner=add_referral_partner,
        remove_referral_partner=remove_referral_partner,
        top_up_referral_partners=top_up_referral_partners,
        referral_partners_registry=referral_partners_registry,
        lido_contracts=lido_contracts,
        tx_params=tx_params
    )

    return (
        referral_partners_registry,
        add_referral_partner,
        remove_referral_partner,
        top_up_referral_partners
    )
