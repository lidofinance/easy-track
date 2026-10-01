from dataclasses import dataclass
import brownie

DEFAULT_NETWORK = "mainnet"


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return CMAddressesSetup(
            module="",
        )
    if network == "hoodi" or network == "hoodi-fork":
        return CMAddressesSetup(
            module="0x87EB69Ae51317405FD285efD2326a4a11f6173b9",
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, hoodi, hoodi-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CMContractsSetup(brownie.interface, cm_addresses=addresses(network))


class CMContractsSetup:
    def __init__(self, interface, cm_addresses):
        assert cm_addresses.module, (
            "CM module address is not set for the selected network; "
            "fill utils/cm.py::addresses before running scenario tests in live mode"
        )
        self.module = interface.ICuratedModule(cm_addresses.module)


@dataclass
class CMAddressesSetup:
    module: str
