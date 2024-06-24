from dataclasses import dataclass
import brownie

DEFAULT_NETWORK = "mainnet"


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        raise NotImplementedError("Mainnet addresses do not exist yet")
    if network == "holesky" or network == "holesky-fork":
        raise NotImplementedError("Holesky addresses do not exist yet")
    if network == "holesky-devnet" or network == "holesky-devnet-fork":
        return CSMAddressesSetup(
            module="0x26aBc20a47f7e8991F1d26Bf0fC2bE8f24E9eF2A",
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, holesky, holesky-fork, holesky-devnet0, holesky-devnet0-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CSMContractsSetup(brownie.interface, csm_addresses=addresses(network))


class CSMContractsSetup:
    def __init__(self, interface, csm_addresses):
        self.module = interface.CSModule(csm_addresses.module)


@dataclass
class CSMAddressesSetup:
    module: str
