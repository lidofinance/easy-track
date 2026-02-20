from dataclasses import dataclass
import brownie

DEFAULT_NETWORK = "mainnet"


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return CMAddressesSetup(
            module="",
        )
    if network == "holesky" or network == "holesky-fork":
        return CMAddressesSetup(
            module="",
        )
    if network == "hoodi" or network == "hoodi-fork":
        return CMAddressesSetup(
            module=""
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, hoodi, hoodi-fork, holesky, holesky-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CMContractsSetup(brownie.interface, cm_addresses=addresses(network))


class CMContractsSetup:
    def __init__(self, interface, cm_addresses):
        self.module = interface.CSModule(cm_addresses.module)


@dataclass
class CMAddressesSetup:
    module: str
