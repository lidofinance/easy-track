from dataclasses import dataclass
import brownie

DEFAULT_NETWORK = "mainnet"


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return CSMAddressesSetup(
            module="0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F",
        )
    if network == "hoodi" or network == "hoodi-fork":
        return CSMAddressesSetup(
            module="0x79CEf36D84743222f37765204Bec41E92a93E59d",
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, hoodi, hoodi-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CSMContractsSetup(brownie.interface, csm_addresses=addresses(network))


class CSMContractsSetup:
    def __init__(self, interface, csm_addresses):
        assert csm_addresses.module, (
            "CSM module address is not set for the selected network; "
            "fill utils/csm.py::addresses before running scenario tests in live mode"
        )
        self.module = interface.CSModule(csm_addresses.module)


@dataclass
class CSMAddressesSetup:
    module: str
