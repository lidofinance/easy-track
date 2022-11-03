
from brownie.network import chain
from brownie import reverts
import pytest

from eth_abi import encode_single
from utils.evm_script import encode_calldata

@pytest.fixture(scope="module")
def allowed_recipients_factory(
    owner,
    entire_allowed_recipients_setup,
    agent,
    finance,
    bokkyPooBahsDateTimeContract,
    AllowedRecipientsFactory
):
    return owner.deploy(
        AllowedRecipientsFactory,
        entire_allowed_recipients_setup.easy_track,
        finance,
        entire_allowed_recipients_setup.evm_script_executor,
        agent,
        bokkyPooBahsDateTimeContract
    )

def test_deploy_full_setup(
    allowed_recipients_factory, stranger, ldo, bokkyPooBahsDateTimeContract
):
    tx = allowed_recipients_factory.deployAllowedRecipientsRegistry(
        [],
        [],
        bokkyPooBahsDateTimeContract,
        1e18,
        1,
        1e18,
        {"from": stranger}
    )
