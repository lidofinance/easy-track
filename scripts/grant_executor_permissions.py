import os
from brownie import interface, ZERO_ADDRESS, network

from utils.lido import contracts, create_voting, execute_voting, permissions
from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    prompt_bool,
)
from utils.evm_script import encode_call_script

acl = contracts()["dao"]["acl"]
lido_permissions = permissions()
required_permissions = [
    lido_permissions.finance.CREATE_PAYMENTS_ROLE,
    lido_permissions.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE,
]


def main():
    vote_id = grant_executor_permissions()
    os.environ["VOTING_ID"] = str(vote_id)
    check_permissions_granted()


def grant_executor_permissions():
    deployer = get_deployer_account(get_is_live())
    evm_script_executor = get_env("EVM_SCRIPT_EXECUTOR")

    granted_permissions = [
        permission
        for permission in required_permissions
        if acl.hasPermission(evm_script_executor, permission.app, permission.role)
    ]

    permissions_to_grant = list(set(required_permissions) - set(granted_permissions))

    if len(granted_permissions) > 0:
        print(f"{evm_script_executor} already granted next roles:")
        for permission in granted_permissions:
            print(f"- {permission}")

    if len(permissions_to_grant) == 0:
        print(f"Has no permissions to grant to {evm_script_executor}")
        return

    print(f"Create voting to grant next roles to {evm_script_executor}:")
    for permission in permissions_to_grant:
        print(f"- {permission}")

    print("Proceed? [y/n]: ")
    if not prompt_bool():
        print("Aborting")
        return

    grant_permissions_evmscript = encode_call_script(
        [
            (
                acl.address,
                acl.grantPermission.encode_input(
                    evm_script_executor, permission.app, permission.role
                ),
            )
            for permission in permissions_to_grant
        ]
    )

    vote_id, _ = create_voting(
        evm_script=grant_permissions_evmscript,
        description="Grant permissions to {evm_script_executor}",
        tx_params={"from": deployer},
    )

    print(f"Vote successfully started! Vote id: {vote_id}")
    return vote_id


def check_permissions_granted():
    voting_id = get_env("VOTING_ID")
    evm_script_executor = get_env("EVM_SCRIPT_EXECUTOR")

    execute_voting(voting_id)

    print(
        f"Validate that {evm_script_executor} has next permissions after voting is passed:"
    )
    for permission in required_permissions:
        print(f"- {permission}")

    for permission in required_permissions:
        assert acl.hasPermission(evm_script_executor, permission.app, permission.role)
    print("Validation Passed!")
