
from brownie.network import chain
from brownie import reverts
import pytest

from eth_abi import encode_single
from utils.evm_script import encode_calldata

@pytest.fixture(scope="module")
def allowed_recipients_factory(owner, AllowedRecipientsFactory):
    return owner.deploy(
        AllowedRecipientsFactory,
        owner,
        owner,
        owner,
        owner
    )

def test_deploy_full_setup(
    allowed_recipients_factory, stranger, ldo
):
    tx = allowed_recipients_factory.deployFullSetup(
        stranger,
        stranger,
        ldo,
        0,
        0,
        {"from": stranger}
    )