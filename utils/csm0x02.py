from dataclasses import dataclass
import brownie

DEFAULT_NETWORK = "mainnet"


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return CSM0x02AddressesSetup(
            module="",
        )
    if network == "hoodi" or network == "hoodi-fork":
        return CSM0x02AddressesSetup(
            module="",
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, hoodi, hoodi-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CSM0x02ContractsSetup(brownie.interface, csm0x02_addresses=addresses(network))


class CSM0x02ContractsSetup:
    def __init__(self, interface, csm0x02_addresses):
        self.module = interface.CSModule(csm0x02_addresses.module)


@dataclass
class CSM0x02AddressesSetup:
    module: str
