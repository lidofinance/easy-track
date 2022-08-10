import constants

from brownie.network import chain
from brownie import LimitsCheckerWrapper, accounts, reverts


def test_limits_checker(limits_checker_wrapper):
    deployer = accounts[0]
    limits_checker_wrapper.setLimit(0)
