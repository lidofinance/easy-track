from dataclasses import dataclass
import brownie
from utils import evm_script as evm_script_utils

DEFAULT_NETWORK = "mainnet"


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        raise NotImplementedError("Mainnet addresses do not exist yet")
    if network == "holesky" or network == "holesky-fork":
        raise NotImplementedError("Holesky addresses do not exist yet")
    if network == "holesky-devnet0" or network == "holesky-devnet0-fork":
        return CSMAddressesSetup(
            accounting="0x9808a94167b30c2F71d2863dbdB8eD9B65ED1DBe",
            fee_distributor="0xFBb0158db5061343Cd130F04FDe71CA62DdBdE2D",
            fee_oracle="0x0Ac2f7145200ce74eEb717C4e36076aC67f1D5E5",
            module="0xddB08564C699D5392a9E9a3C8E2Ab9D7C1949CB6",
            verifier="0x57A3807E89cfC10dA48e90D994b5dCa15d595ABb",
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, holesky, holesky-fork, holesky-devnet0, holesky-devnet0-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CSMContractsSetup(brownie.interface, csm_addresses=addresses(network))


class CSMContractsSetup:
    def __init__(self, interface, csm_addresses):
        self.accounting = interface.CSAccounting(csm_addresses.accounting)
        self.fee_distributor = interface.CSFeeDistributor(csm_addresses.fee_distributor)
        self.fee_oracle = interface.CSFeeOracle(csm_addresses.fee_oracle)
        self.module = interface.CSModule(csm_addresses.module)
        self.verifier = interface.CSVerifier(csm_addresses.verifier)


@dataclass
class CSMAddressesSetup:
    accounting: str
    fee_distributor: str
    fee_oracle: str
    module: str
    verifier: str
