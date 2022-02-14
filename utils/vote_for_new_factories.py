from typing import NamedTuple, List, Dict
from utils import lido
from utils.evm_script import encode_call_script

from brownie import (Contract, EasyTrack)

class FactoryToAdd(NamedTuple):
    factory: Contract
    permissions: str

def create_voting_on_ref_partners_factories(
    easy_track: EasyTrack,
    factories: List[FactoryToAdd],
    network: str,
    tx_params: Dict[str, str]
) -> int:
    add_factories_evm_script: str = encode_call_script(
        [
            (
                easy_track.address,
                easy_track.addEVMScriptFactory.encode_input(
                    elem.factory,
                    elem.permissions
                )
            )
            for elem in factories
        ]
    )

    description: str = 'Omnibus vote:'
    item_id: int = 1
    for elem in factories:
        description += f'{item_id} Add {elem.factory} factory'
        item_id = item_id + 1

    vote_id, _ = lido.create_voting(
        evm_script=add_factories_evm_script,
        description=description,
        network=network,
        tx_params=tx_params,
    )
    return vote_id
