from brownie import network
from scripts.revoke_all_permissions import revoke_permissions
from scripts.grant_executor_permissions import grant_executor_permissions
from scripts.deploy import deploy_easy_tracks
from utils import lido


def test_revoke_permissions(accounts):
    lido_contracts = lido.contracts(network=network.show_active())
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

    permissions = [
        lido_permissions.finance.CREATE_PAYMENTS_ROLE,
        lido_permissions.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE,
    ]
    lido_contracts.ldo.transfer(
        deployer, 10 ** 18, {"from": lido_contracts.aragon.agent}
    )
    voting_id = grant_executor_permissions(
        lido_contracts=lido_contracts,
        evm_script_executor=evm_script_executor.address,
        permissions_to_grant=permissions,
        tx_params={"from": deployer},
    )

    lido_contracts.execute_voting(voting_id)

    for permission in permissions:
        assert lido_contracts.aragon.acl.hasPermission(
            evm_script_executor, permission.app, permission.role
        )

    voting_id = revoke_permissions(
        lido_contracts=lido_contracts,
        granted_permissions=permissions,
        evm_script_executor=evm_script_executor,
        tx_params={"from": deployer},
    )

    lido_contracts.execute_voting(voting_id)

    for permission in lido_permissions.all():
        assert not lido_contracts.aragon.acl.hasPermission(
            evm_script_executor, permission.app, permission.role
        )
