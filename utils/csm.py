from dataclasses import dataclass
import brownie

DEFAULT_NETWORK = "mainnet"


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        raise NotImplementedError("Mainnet addresses do not exist yet")
    if network == "holesky" or network == "holesky-fork":
        raise NotImplementedError("Holesky addresses do not exist yet")
    if network == "holesky-devnet0" or network == "holesky-devnet0-fork":
        return CSMAddressesSetup(
            module="0xddB08564C699D5392a9E9a3C8E2Ab9D7C1949CB6",
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
