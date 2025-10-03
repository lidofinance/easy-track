import os
import sys
from brownie import network, accounts, web3
from utils import lido
from typing import Optional


def get_network_name() -> Optional[str]:
    full_network_name = network.show_active()

    if full_network_name is None:
        cli_args = sys.argv[1:]
        net_ind = next((cli_args.index(arg) for arg in cli_args if arg == "--network"), len(cli_args))
        if net_ind != len(cli_args):
            full_network_name = cli_args[net_ind + 1]

    return full_network_name.split("-")[0]


def get_is_live():
    dev_networks = ["development", "hardhat", "hardhat-fork", "mainnet-fork", "holesky-fork", "hoodi-fork"]
    return network.show_active() not in dev_networks


def get_deployer_account(is_live, network="mainnet"):
    if not is_live:
        deployer = accounts[0]
        contracts = lido.contracts(network=network)
        set_balance_in_wei(contracts.aragon.agent.address, 100 * 10**18)
        contracts.ldo.transfer(deployer, 10**18, {"from": contracts.aragon.agent, "gas_price": "100 gwei"})
        return deployer
    if "DEPLOYER" not in os.environ:
        raise EnvironmentError("Please set DEPLOYER env variable to the deployer account name")

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

def set_balance_in_wei(address, balance):
    account = accounts.at(address, force=True)
    providers = ["evm_setAccountBalance", "hardhat_setBalance", "anvil_setBalance"]

    for provider in providers:
        if account.balance() == balance:
            break

        try:
            web3.provider.make_request(provider, [address, hex(balance)])
        except ValueError as e:
            if e.args[0].get("message") != f"Method {provider} is not supported":
                raise e

    assert account.balance() == balance, f"Failed to set balance {balance} for account: {address}"
    return account