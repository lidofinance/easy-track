from hexbytes import HexBytes
from utils.publish_source import publish_source
from utils import log

from brownie import (
    network,
    AddAllowedRecipient,
    AllowedRecipientsRegistry,
    RemoveAllowedRecipient,
    TopUpAllowedRecipients
)

def verify_contracts_by_tx(tx_of_creation):

    tx = network.chain.get_transaction(tx_of_creation)

    if "AllowedRecipientsRegistryDeployed" in tx.events:
        regestry_address = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
        log.nb(f"AllowedRecipientsRegistry found at {regestry_address}")
        regestry = AllowedRecipientsRegistry.at(regestry_address)
        create_event = [d for d in tx.logs if d["topics"][0] == HexBytes("0x624dc458b1e9b01142ed5c06473d7d1a08d219ba663d603b9533edf82821167e")]
        if create_event[0]:
            log.nb(f"constructor params found: {create_event[0].data}")
            publish_source(regestry, AllowedRecipientsRegistry, create_event[0].data[2:])
    
    if "TopUpAllowedRecipientsDeployed" in tx.events:
        top_up_address = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
        log.nb(f"TopUpAllowedRecipients found at {top_up_address}")
        top_up_contract = TopUpAllowedRecipients.at(top_up_address)
        create_event = [d for d in tx.logs if d["topics"][0] == HexBytes("0x1c087496889e1b9b250244777717d8c84455741fa048f887a8c861e0c667694b")]
        if create_event[0]:
            log.nb(f"constructor params found: {create_event[0].data}")
            publish_source(top_up_contract, TopUpAllowedRecipients, create_event[0].data[2:])
    
    if "AddAllowedRecipientDeployed" in tx.events:
        add_recipient_address = tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
        log.nb(f"AddAllowedRecipient found at {add_recipient_address}")
        add_contract = AddAllowedRecipient.at(add_recipient_address)
        create_event = [d for d in tx.logs if d["topics"][0] == HexBytes("0x272f7c64031716b189f8cd77394a9f9a335b9cc580f94d03c635f880cd678555")]
        if create_event[0]:
            log.nb(f"constructor params found: {create_event[0].data}")
            publish_source(add_contract, AddAllowedRecipient, create_event[0].data[2:])

    if "RemoveAllowedRecipientDeployed" in tx.events:
        remove_recipient_address = tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]
        log.nb(f"RemoveAllowedRecipient found at {remove_recipient_address}")
        removeContract = RemoveAllowedRecipient.at(remove_recipient_address)
        create_event = [d for d in tx.logs if d["topics"][0] == HexBytes("0x5db4d6a86ad8029c995cd626dd25c892af2bd4c15877c68eacbbaecc7a1f18d4")]
        if create_event[0]:
            log.nb(f"constructor params found: {create_event[0].data}")
            publish_source(regestry, RemoveAllowedRecipient, create_event[0].data[2:])
