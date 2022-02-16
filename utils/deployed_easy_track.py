from typing import Optional
from brownie import (
    EasyTrack,
    EVMScriptExecutor,
    AddReferralPartner,
    RemoveReferralPartner,
    TopUpReferralPartners,
    ReferralPartnersRegistry,
    Contract
)

def addresses(network="mainnet"):
    if network == "mainnet":
        return EasyTrackSetup(
            easy_track="0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            evm_script_executor="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977",
            referral_partners_registry=None,
            add_referral_partner=None,
            remove_referral_partner=None,
            top_up_referral_partners=None
        )
    if network == "goerli":
        return EasyTrackSetup(
            easy_track="0xAf072C8D368E4DD4A9d4fF6A76693887d6ae92Af",
            evm_script_executor="0x3c9aca237b838c59612d79198685e7f20c7fe783",
            referral_partners_registry="0xBB4C830275F121F7ecaCE8C5526cc8102752eED0",
            add_referral_partner="0x1fDEdCd6fcFD009b0B1B751aceEAF16dDb228384",
            remove_referral_partner="0x42b608642C6AD8f3b210093ded7dc53fc1001492",
            top_up_referral_partners="0xDEbAf563F737Ee0EE7A31DFea478c5034DB3804B"
        )
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, goerli."""
    )

def contract_or_none(
    contract: Contract,
    addr: Optional[str]
) -> Optional[Contract]:
    if not addr:
        return None
    return contract.at(addr)


def contracts(network="mainnet"):
    network_addresses = addresses(network)
    return EasyTrackSetup(
        easy_track=contract_or_none(EasyTrack, network_addresses.easy_track),
        evm_script_executor=contract_or_none(EVMScriptExecutor, network_addresses.evm_script_executor),
        referral_partners_registry=contract_or_none(ReferralPartnersRegistry, network_addresses.referral_partners_registry),
        add_referral_partner=contract_or_none(AddReferralPartner, network_addresses.add_referral_partner),
        remove_referral_partner=contract_or_none(RemoveReferralPartner, network_addresses.remove_referral_partner),
        top_up_referral_partners=contract_or_none(TopUpReferralPartners, network_addresses.top_up_referral_partners)
    )

class EasyTrackSetup:
    def __init__(
        self,
        easy_track,
        evm_script_executor,
        add_referral_partner,
        remove_referral_partner,
        top_up_referral_partners,
        referral_partners_registry
    ):
        self.easy_track = easy_track
        self.evm_script_executor = evm_script_executor
        self.add_referral_partner = add_referral_partner
        self.remove_referral_partner = remove_referral_partner
        self.top_up_referral_partners = top_up_referral_partners
        self.referral_partners_registry = referral_partners_registry
