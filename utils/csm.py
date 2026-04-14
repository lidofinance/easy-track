from dataclasses import dataclass
import os
import brownie

DEFAULT_NETWORK = "mainnet"


def _env(name):
    if name not in os.environ or os.environ[name] == "":
        raise EnvironmentError(f"Please set {name} env variable")
    return os.environ[name]


def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return CSMAddressesSetup(
            module="0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F",
            allowed_merkle_gates_registry="",
        )
    if network == "hoodi" or network == "hoodi-fork":
        return CSMAddressesSetup(
            module="0x79CEf36D84743222f37765204Bec41E92a93E59d",
            allowed_merkle_gates_registry="",
        )
    if network == "devnet" or network == "devnet-fork":
        return CSMAddressesSetup(
            module=_env("CSM_MODULE_ADDRESS"),
            allowed_merkle_gates_registry=_env("CSM_ALLOWED_MERKLE_GATES_REGISTRY_ADDRESS"),
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, hoodi, hoodi-fork, devnet, devnet-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CSMContractsSetup(brownie.interface, csm_addresses=addresses(network))


class CSMContractsSetup:
    def __init__(self, interface, csm_addresses):
        self.module = interface.CSModule(csm_addresses.module)
        self.allowed_merkle_gates_registry = interface.IAllowedMerkleGatesRegistry(
            csm_addresses.allowed_merkle_gates_registry
        )


@dataclass
class CSMAddressesSetup:
    module: str
    allowed_merkle_gates_registry: str
