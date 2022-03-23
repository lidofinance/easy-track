import os
import sys
from brownie import network, accounts
from utils import lido
from typing import Optional

def network_name() -> Optional[str]:
    if network.show_active() != None:
        return network.show_active()
    cli_args = sys.argv[1:]
    net_ind = next((cli_args.index(arg) for arg in cli_args if arg == '--network'), len(cli_args))
    net_name = None
    if net_ind != len(cli_args):
        net_name = cli_args[net_ind+1]
    return net_name

def get_is_live():
    dev_networks = [
        "development",
        "hardhat",
        "hardhat-fork",
        "mainnet-fork",
        "goerli-fork"
    ]
    return network.show_active() not in dev_networks


def get_deployer_account(is_live, network="mainnet"):
    contracts = lido.contracts(network=network)
    if not is_live:
        deployer = accounts[0]
        contracts.ldo.transfer(deployer, 10 ** 18, {"from": contracts.aragon.agent})
        return deployer
    if "DEPLOYER" not in os.environ:
        raise EnvironmentError(
            "Please set DEPLOYER env variable to the deployer account name"
        )

    return accounts.load(os.environ["DEPLOYER"])


def prompt_bool():
    choice = input().lower()
    if choice in {"yes", "y"}:
        return True
    elif choice in {"no", "n"}:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'")


def get_env(name, default=None):
    if name not in os.environ:
        if default is not None:
            return default
        raise EnvironmentError(f"Please set {name} env variable")
    return os.environ[name]
