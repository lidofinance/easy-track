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
        return CMAddressesSetup(
            module="",
            meta_registry="",
            allowed_merkle_gates_registry="",
        )
    if network == "hoodi" or network == "hoodi-fork":
        return CMAddressesSetup(
            module="",
            meta_registry="",
            allowed_merkle_gates_registry="",
        )
    if network == "devnet" or network == "devnet-fork":
        return CMAddressesSetup(
            module=_env("CM_MODULE_ADDRESS"),
            meta_registry=_env("CM_META_REGISTRY_ADDRESS"),
            allowed_merkle_gates_registry=_env("CM_ALLOWED_MERKLE_GATES_REGISTRY_ADDRESS"),
        )
    raise NameError(
        f"Unknown network '{network}'. Supported networks: mainnet, mainnet-fork, hoodi, hoodi-fork, devnet, devnet-fork"
    )


def contracts(network=DEFAULT_NETWORK):
    return CMContractsSetup(brownie.interface, cm_addresses=addresses(network))


class CMContractsSetup:
    def __init__(self, interface, cm_addresses):
        self.module = interface.CSModule(cm_addresses.module)
        self.meta_registry = interface.IMetaRegistry(cm_addresses.meta_registry)
        self.allowed_merkle_gates_registry = interface.IAllowedMerkleGatesRegistry(
            cm_addresses.allowed_merkle_gates_registry
        )


@dataclass
class CMAddressesSetup:
    module: str
    meta_registry: str
    allowed_merkle_gates_registry: str
