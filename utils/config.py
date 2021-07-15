import os
import sys
from brownie import network, accounts
from utils.lido import contracts


def get_is_live():
    return network.show_active() != "development"


def get_deployer_account(is_live):
    if not is_live:
        ldo = contracts()["dao"]["ldo"]
        agent = contracts()["dao"]["agent"]
        deployer = accounts[0]
        ldo.transfer(deployer, 10 ** 18, {"from": agent})
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
