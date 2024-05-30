import brownie
from scripts.grant_executor_permissions import grant_executor_permissions
from scripts.deploy import deploy_easy_tracks
from utils import lido


def test_grant_executor_permissions(accounts, lido_contracts):
    deployer = accounts[0]
    lego_program_vault = accounts[1]
    lego_committee_multisig = accounts[2]
    reward_programs_multisig = accounts[3]
    pause_address = accounts[4]
    evm_script_executor = deploy_easy_tracks(
        lido_contracts=lido_contracts,
        lego_program_vault=lego_program_vault,
        lego_committee_multisig=lego_committee_multisig,
        reward_programs_multisig=reward_programs_multisig,
        pause_address=pause_address,
        tx_params={"from": deployer},
    )[1]

    lido_permissions = lido_contracts.permissions
    required_permissions = [
        lido_permissions.finance.CREATE_PAYMENTS_ROLE,
        lido_permissions.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE,
    ]

    for permission in required_permissions:
        assert not lido_contracts.aragon.acl.hasPermission(evm_script_executor, permission.app, permission.role)

    lido_contracts.ldo.transfer(deployer, 10**18, {"from": lido_contracts.aragon.agent})
    voting_id = grant_executor_permissions(
        lido_contracts=lido_contracts,
        evm_script_executor=evm_script_executor.address,
        permissions_to_grant=required_permissions,
        tx_params={"from": deployer},
    )

    lido_contracts.execute_voting(voting_id)

    for permission in required_permissions:
        assert lido_contracts.aragon.acl.hasPermission(evm_script_executor, permission.app, permission.role)
