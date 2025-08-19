from scripts.revoke_all_permissions import revoke_permissions
from scripts.grant_executor_permissions import grant_executor_permissions
from scripts.deploy import deploy_easy_tracks

from utils import evm_script
from utils.dual_governance import submit_proposals, process_pending_proposals


def test_revoke_permissions(accounts, agent, lido_contracts):
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

    grant_permission_manager_voting, _ = lido_contracts.create_voting(
        evm_script=evm_script.encode_call_script(
            submit_proposals(
                [
                    (
                        [
                            (
                                agent.address,
                                agent.forward.encode_input(
                                    evm_script.encode_call_script(
                                        [
                                            (
                                                lido_contracts.aragon.acl.address,
                                                lido_contracts.aragon.acl.setPermissionManager.encode_input(
                                                    lido_contracts.aragon.voting,
                                                    lido_contracts.node_operators_registry,
                                                    lido_permissions.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE.role,
                                                ),
                                            )
                                        ]
                                    )
                                ),
                            )
                        ],
                        "Grant permission manager to Voting",
                    )
                ]
            ),
        ),
        description="Grant permission manager to Voting",
        tx_params={"from": agent},
    )

    lido_contracts.execute_voting(grant_permission_manager_voting)
    process_pending_proposals()

    permissions = [
        lido_permissions.finance.CREATE_PAYMENTS_ROLE,
        lido_permissions.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE,
    ]
    lido_contracts.ldo.transfer(deployer, 10**18, {"from": lido_contracts.aragon.agent})
    voting_id = grant_executor_permissions(
        lido_contracts=lido_contracts,
        evm_script_executor=evm_script_executor.address,
        permissions_to_grant=permissions,
        tx_params={"from": deployer},
    )

    lido_contracts.execute_voting(voting_id)

    for permission in permissions:
        assert lido_contracts.aragon.acl.hasPermission(evm_script_executor, permission.app, permission.role)

    voting_id = revoke_permissions(
        lido_contracts=lido_contracts,
        granted_permissions=permissions,
        evm_script_executor=evm_script_executor,
        tx_params={"from": deployer},
    )

    lido_contracts.execute_voting(voting_id)

    for permission in lido_permissions.all():
        assert not lido_contracts.aragon.acl.hasPermission(evm_script_executor, permission.app, permission.role)
