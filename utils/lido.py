from brownie import chain, network, accounts, interface
from utils.evm_script import encode_call_script

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
        "node_operators_registry": "0x55032650b14df07b85bf18a3a3ec8e0af2e028d5",
        "steth": "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
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
        "node_operators_registry": "0x9D4AF1Ee19Dad8857db3a45B0374c81c8A1C6320",
        "steth": "0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F",
    },
}


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
        },
        "node_operators_registry": interface.NodeOperatorsRegistry(
            addresses["node_operators_registry"]
        ),
        "steth": interface.Lido(addresses["steth"]),
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


class Permission:
    def __init__(self, app, role_name):
        self.app = app
        self.role_name = role_name
        self.role = getattr(app, role_name)()

    def __str__(self):
        return f"{self.app._name}.{self.role_name}"
