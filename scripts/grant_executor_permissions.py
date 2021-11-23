from utils import lido
from utils.evm_script import encode_call_script
from utils.config import get_env, get_is_live, get_deployer_account, prompt_bool


def main():
    deployer = get_deployer_account(get_is_live())
    evm_script_executor = get_env("EVM_SCRIPT_EXECUTOR")

    lido_contracts = lido.contracts(network="mainnet")
    lido_permissions = lido.permissions(contracts=lido_contracts)

    required_permissions = [
        lido_permissions.finance.CREATE_PAYMENTS_ROLE,
        lido_permissions.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE,
    ]

    acl = lido_contracts.aragon.acl

    granted_permissions = lido_permissions.filter_granted(
        permissions=required_permissions, address=evm_script_executor
    )

    permissions_to_grant = list(set(required_permissions) - set(granted_permissions))

    print(f"Deployer: {deployer}")
    print(f"EVMScriptExecutor address: {evm_script_executor}")

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

    tx_params = {
        "from": deployer,
        "gas_price": "100 gwei"
        # "priority_fee": "4 gwei",
    }
    vote_id = grant_executor_permissions(
        acl=acl,
        evm_script_executor=evm_script_executor,
        permissions_to_grant=permissions_to_grant,
        tx_params=tx_params,
    )
    print(f"Vote successfully started! Vote id: {vote_id}")


def get_permissions_to_grant(permissions, granted_permissions):
    return list(set(permissions) - set(granted_permissions))


def grant_executor_permissions(
    acl, evm_script_executor, permissions_to_grant, tx_params
):
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

    vote_id, _ = lido.create_voting(
        evm_script=grant_permissions_evmscript,
        description="Grant permissions to {evm_script_executor}",
        tx_params=tx_params,
    )
    return vote_id
