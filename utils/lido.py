from brownie import chain, network, accounts, interface
from utils.evm_script import encode_call_script


PERMISSIONS = {
    "agent": [
        "ADD_PROTECTED_TOKEN_ROLE",
        "TRANSFER_ROLE",
        "RUN_SCRIPT_ROLE",
        "SAFE_EXECUTE_ROLE",
        "REMOVE_PROTECTED_TOKEN_ROLE",
        "DESIGNATE_SIGNER_ROLE",
        "EXECUTE_ROLE",
        "ADD_PRESIGNED_HASH_ROLE",
    ],
    "finance": [
        "CREATE_PAYMENTS_ROLE",
        "CHANGE_PERIOD_ROLE",
        "CHANGE_BUDGETS_ROLE",
        "EXECUTE_PAYMENTS_ROLE",
        "MANAGE_PAYMENTS_ROLE",
    ],
    "lido": [
        "PAUSE_ROLE",
        "SET_ORACLE",
        "MANAGE_WITHDRAWAL_KEY",
        "MANAGE_FEE",
        "SET_TREASURY",
        "BURN_ROLE",
        "SET_INSURANCE_FUND",
    ],
    "node_operators_registry": [
        "SET_NODE_OPERATOR_ADDRESS_ROLE",
        "SET_NODE_OPERATOR_NAME_ROLE",
        "ADD_NODE_OPERATOR_ROLE",
        "REPORT_STOPPED_VALIDATORS_ROLE",
        "SET_NODE_OPERATOR_ACTIVE_ROLE",
        "SET_NODE_OPERATOR_LIMIT_ROLE",
        "MANAGE_SIGNING_KEYS",
    ],
    "oracle": [
        "MANAGE_QUORUM",
        "SET_BEACON_REPORT_RECEIVER",
        "MANAGE_MEMBERS",
        "SET_BEACON_SPEC",
        "SET_REPORT_BOUNDARIES",
    ],
    "tokens": [
        "ISSUE_ROLE",
        "ASSIGN_ROLE",
        "BURN_ROLE",
        "MINT_ROLE",
        "REVOKE_VESTINGS_ROLE",
    ],
    "voting": ["MODIFY_QUORUM_ROLE", "MODIFY_SUPPORT_ROLE", "CREATE_VOTES_ROLE"],
}

CONTRACT_ADDRESSES = {
    "mainnet": {
        "dao": {
            "agent": "0x3e40d73eb977dc6a537af587d48316fee66e9c8c",
            "ldo": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",
            "voting": "0x2e59a20f205bb85a89c53f1936454680651e618e",
            "tokens": "0xf73a1260d222f447210581ddf212d915c09a3249",
            "acl": "0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb",
            "finance": "0xb9e5cbb9ca5b0d659238807e84d0176930753d86",
            "calls_script": "0x5cEb19e1890f677c3676d5ecDF7c501eBA01A054",
        },
        "lido": "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
        "oracle": "0x442af784A788A5bd6F42A01Ebe9F287a871243fb",
        "node_operators_registry": "0x55032650b14df07b85bf18a3a3ec8e0af2e028d5",
    },
    "goerli": {
        "dao": {
            "agent": "0x4333218072d5d7008546737786663c38b4d561a4",
            "ldo": "0x56340274fB5a72af1A3C6609061c451De7961Bd4",
            "voting": "0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db",
            "tokens": "0xdfe76d11b365f5e0023343a367f0b311701b3bc1",
            "acl": "0xb3cf58412a00282934d3c3e73f49347567516e98",
            "finance": "0x75c7b1d23f1cad7fb4d60281d7069e46440bc179",
            "calls_script": "0x1b4fb0c1357afd3f267c5e897ecfec75938c7436",
        },
        "lido": "0x1643e812ae58766192cf7d2cf9567df2c37e9b7f",
        "oracle": "0x24d8451bc07e7af4ba94f69acdd9ad3c6579d9fb",
        "node_operators_registry": "0x9d4af1ee19dad8857db3a45b0374c81c8a1c6320",
    },
}


def permissions():
    return Permissions()


def all_permissions():
    res = []
    permissions = Permissions()
    for app_name in PERMISSIONS.keys():
        app = getattr(permissions, app_name)
        for role_name in PERMISSIONS[app_name]:
            res.append(getattr(app, role_name))
    return res


def create_contracts(interface, addresses):
    return {
        "dao": {
            "agent": interface.Agent(addresses["dao"]["agent"]),
            "ldo": interface.MiniMeToken(addresses["dao"]["ldo"]),
            "voting": interface.Voting(addresses["dao"]["voting"]),
            "tokens": interface.TokenManager(addresses["dao"]["tokens"]),
            "acl": interface.ACL(addresses["dao"]["acl"]),
            "finance": interface.Finance(addresses["dao"]["finance"]),
            "calls_script": interface.CallsScript(addresses["dao"]["calls_script"]),
            "oracle": interface.Oracle(addresses["oracle"]),
        },
        "lido": interface.Lido(addresses["lido"]),
        "node_operators_registry": interface.NodeOperatorsRegistry(
            addresses["node_operators_registry"]
        ),
    }


def contracts(interface=interface):
    network_name = network.show_active()
    if network_name == "mainnet-fork":
        return create_contracts(interface, CONTRACT_ADDRESSES["mainnet"])
    if network_name == "development":
        if chain.id == 1:
            return create_contracts(interface, CONTRACT_ADDRESSES["mainnet"])
        elif chain.id == 5:
            return create_contracts(interface, CONTRACT_ADDRESSES["goerli"])
        else:
            raise NameError(f"Unsupported chain id '{chain.id}'")
    if not network_name in CONTRACT_ADDRESSES:
        raise NameError(f"Unsupported network '{network_name}'")
    return create_contracts(interface, CONTRACT_ADDRESSES[network_name])


def create_voting(evm_script, description, tx_params):
    agent = contracts()["dao"]["agent"]
    voting = contracts()["dao"]["voting"]
    tokens = contracts()["dao"]["tokens"]

    voting_tx = tokens.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.newVote.encode_input(evm_script, description),
                )
            ]
        ),
        tx_params or {"from": agent},
    )
    return voting_tx.events["StartVote"]["voteId"], voting_tx


def execute_voting(voting_id):
    agent = contracts()["dao"]["agent"]
    voting = contracts()["dao"]["voting"]
    if voting.getVote(voting_id)["executed"]:
        return
    voting.vote(voting_id, True, False, {"from": agent})
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(voting_id)
    voting.executeVote(voting_id, {"from": accounts[0]})

class AppPermissions:
    def __init__(self, app, permission_names):
        self.app = app
        self.permission_names = permission_names

    def __getattr__(self, name):
        if name not in self.permission_names:
            raise NameError(f"Permission {name} not found in app {self.app._name}")
        return Permission(self.app, name)


class Permissions:
    def __init__(self):
        self.contracts = contracts()

    def __getattr__(self, name):
        app = (
            self.contracts[name]
            if name in self.contracts
            else self.contracts["dao"][name]
        )
        if name not in PERMISSIONS or app is None:
            raise AttributeError(f"Application {name} not found in Lido")
        return AppPermissions(app, PERMISSIONS[name])


class Permission:
    def __init__(self, app, role_name):
        self.app = app
        self.role_name = role_name
        self.role = getattr(app, role_name)()

    def __hash__(self):
        return hash((self.app, self.role_name))

    def __eq__(self, o):
        if isinstance(o, Permission):
            return self.app == o.app and self.role_name == o.role_name
        return False

    def __str__(self):
        return f"{self.app._name}.{self.role_name}"

