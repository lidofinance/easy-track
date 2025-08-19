import brownie
from typing import NamedTuple, List, Dict
from utils import lido, log
from utils.config import prompt_bool
from utils.evm_script import encode_call_script

from brownie import Contract, EasyTrack


class FactoryToAdd(NamedTuple):
    factory: Contract
    permissions: str


class FactoryToRemove(NamedTuple):
    factory: Contract


def create_voting_on_new_factories(
    easy_track: EasyTrack,
    factories_to_add: List[FactoryToAdd],
    factories_to_remove: List[FactoryToRemove],
    network: str,
    tx_params: Dict[str, str],
) -> int:
    factories_evm_script: str = encode_call_script(
        [
            (
                easy_track.address,
                easy_track.removeEVMScriptFactory.encode_input(elem.factory),
            )
            for elem in factories_to_remove
        ]
        + [
            (
                easy_track.address,
                easy_track.addEVMScriptFactory.encode_input(elem.factory, elem.permissions),
            )
            for elem in factories_to_add
        ]
    )

    description: str = "Omnibus vote:"
    item_id: int = 1
    for elem in factories_to_remove:
        description += f"{item_id}) Remove {elem.factory} factory;"
        item_id = item_id + 1

    for elem in factories_to_add:
        description += f"{item_id}) Add {elem.factory} factory;"
        item_id = item_id + 1
    description = description[:-1] + "."

    print(description.replace(";", "\n"))

    print("Proceed to create vote? [yes/no]: ")

    if not prompt_bool():
        log.nb("Aborting")
        return -1

    lido_contracts = lido.contracts(network=brownie.network.show_active())

    vote_id, _ = lido_contracts.create_voting(
        evm_script=factories_evm_script,
        description=description,
        tx_params=tx_params,
    )
    return vote_id
