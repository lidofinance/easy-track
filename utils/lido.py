import brownie
from utils import evm_script as evm_script_utils

DEFAULT_NETWORK = "mainnet"

def addresses(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return LidoAddressesSetup(
            aragon=AragonSetup(
                acl="0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb",
                agent="0x3e40d73eb977dc6a537af587d48316fee66e9c8c",
                voting="0x2e59a20f205bb85a89c53f1936454680651e618e",
                finance="0xb9e5cbb9ca5b0d659238807e84d0176930753d86",
                gov_token="0x5a98fcbea516cf06857215779fd812ca3bef1b32",
                calls_script="0x5cEb19e1890f677c3676d5ecDF7c501eBA01A054",
                token_manager="0xf73a1260d222f447210581ddf212d915c09a3249",
            ),
            steth="0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
            node_operators_registry="0x55032650b14df07b85bf18a3a3ec8e0af2e028d5",
        )
    if network == "goerli" or network == "goerli-fork":
        return LidoAddressesSetup(
            aragon=AragonSetup(
                acl="0xb3cf58412a00282934d3c3e73f49347567516e98",
                agent="0x4333218072d5d7008546737786663c38b4d561a4",
                voting="0xbc0B67b4553f4CF52a913DE9A6eD0057E2E758Db",
                finance="0x75c7b1d23f1cad7fb4d60281d7069e46440bc179",
                gov_token="0x56340274fB5a72af1A3C6609061c451De7961Bd4",
                calls_script="0x1b4fb0c1357afd3f267c5e897ecfec75938c7436",
                token_manager="0xdfe76d11b365f5e0023343a367f0b311701b3bc1",
            ),
            steth="0x1643e812ae58766192cf7d2cf9567df2c37e9b7f",
            node_operators_registry="0x9d4af1ee19dad8857db3a45b0374c81c8a1c6320",
        )
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, mainnet-fork goerli, goerli-fork"""
    )


def contracts(network=DEFAULT_NETWORK):
    return LidoContractsSetup(brownie.interface, lido_addresses=addresses(network))

def external_contracts(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return {
            "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        }
    if network == "goerli" or network == "goerli-fork":
        return {
            "usdc": "0x07865c6E87B9F70255377e024ace6630C1Eaa37F"
        }
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, mainnet-fork goerli, goerli-fork"""
    )


def allowed_recipients_builder(network=DEFAULT_NETWORK):
    if network == "mainnet" or network == "mainnet-fork":
        return brownie.AllowedRecipientsBuilder.at(
            "0x958e0D946D014F377421a53AB5f9180d4485e63B"
        )
    if network == "goerli" or network == "goerli-fork":
        return brownie.AllowedRecipientsBuilder.at(
            "0x1082512D1d60a0480445353eb55de451D261b684"
        )
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, mainnet-fork goerli, goerli-fork"""
    )


class LidoContractsSetup:
    def __init__(self, interface, lido_addresses):
        self.lido_addresses = lido_addresses
        self.aragon = AragonSetup(
            acl=interface.ACL(lido_addresses.aragon.acl),
            agent=interface.Agent(lido_addresses.aragon.agent),
            voting=interface.Voting(lido_addresses.aragon.voting),
            finance=interface.Finance(lido_addresses.aragon.finance),
            gov_token=interface.MiniMeToken(lido_addresses.aragon.gov_token),
            calls_script=interface.CallsScript(lido_addresses.aragon.calls_script),
            token_manager=interface.TokenManager(lido_addresses.aragon.token_manager),
        )
        self.steth = interface.Lido(lido_addresses.steth)
        self.node_operators_registry = interface.NodeOperatorsRegistry(
            lido_addresses.node_operators_registry
        )
        self.ldo = self.aragon.gov_token
        self.permissions = Permissions(contracts=self)

    def create_voting(self, evm_script, description, tx_params=None):
        voting = self.aragon.voting

        voting_tx = self.aragon.token_manager.forward(
            evm_script_utils.encode_call_script(
                [
                    (
                        voting.address,
                        voting.newVote.encode_input(evm_script, description),
                    )
                ]
            ),
            tx_params or {"from": self.aragon.agent},
        )
        return voting_tx.events["StartVote"]["voteId"], voting_tx

    def execute_voting(self, voting_id):
        voting = self.aragon.voting
        if voting.getVote(voting_id)["executed"]:
            return
        ldo_holders = [self.aragon.agent]
        for holder_addr in ldo_holders:
            if not voting.canVote(voting_id, holder_addr):
                print(f"{holder_addr} can't vote in voting {voting_id}")
                continue
            brownie.accounts[0].transfer(holder_addr, "0.1 ether")
            account = brownie.accounts.at(holder_addr, force=True)
            voting.vote(voting_id, True, False, {"from": account})

        brownie.chain.sleep(3 * 60 * 60 * 24)
        brownie.chain.mine()
        assert voting.canExecute(voting_id)
        voting.executeVote(voting_id, {"from": brownie.accounts[0]})


class LidoAddressesSetup:
    def __init__(self, aragon, steth, node_operators_registry):
        self.aragon = aragon
        self.steth = steth
        self.node_operators_registry = node_operators_registry
        self.ldo = self.aragon.gov_token


class AragonSetup:
    def __init__(
        self, acl, agent, voting, finance, gov_token, calls_script, token_manager
    ):
        self.acl = acl
        self.agent = agent
        self.voting = voting
        self.finance = finance
        self.gov_token = gov_token
        self.calls_script = calls_script
        self.token_manager = token_manager


class Permissions:
    def __init__(self, contracts):
        self._acl = contracts.aragon.acl
        self.finance = FinancePermissions(contracts.aragon.finance)
        self.agent = AgentPermissions(contracts.aragon.agent)
        self.lido = LidoPermissions(contracts.steth)
        self.node_operators_registry = NodeOperatorsRegistryPermissions(
            contracts.node_operators_registry
        )
        self.token_manager = TokenManagerPermissions(contracts.aragon.token_manager)
        self.voting = VotingPermissions(contracts.aragon.voting)

    def filter_granted(self, permissions, address):
        return [
            permission
            for permission in permissions
            if self._acl.hasPermission(address, permission.app, permission.role)
        ]

    def all(self):
        return (
            list(self.finance.__dict__.values())
            + list(self.agent.__dict__.values())
            + list(self.lido.__dict__.values())
            + list(self.node_operators_registry.__dict__.values())
            + list(self.token_manager.__dict__.values())
            + list(self.voting.__dict__.values())
        )


class FinancePermissions:
    def __init__(self, finance_app):
        self.CREATE_PAYMENTS_ROLE = Permission(finance_app, "CREATE_PAYMENTS_ROLE")
        self.CHANGE_PERIOD_ROLE = Permission(finance_app, "CHANGE_PERIOD_ROLE")
        self.CHANGE_BUDGETS_ROLE = Permission(finance_app, "CHANGE_BUDGETS_ROLE")
        self.EXECUTE_PAYMENTS_ROLE = Permission(finance_app, "EXECUTE_PAYMENTS_ROLE")
        self.MANAGE_PAYMENTS_ROLE = Permission(finance_app, "MANAGE_PAYMENTS_ROLE")


class AgentPermissions:
    def __init__(self, agent_app):
        self.ADD_PROTECTED_TOKEN_ROLE = Permission(
            agent_app, "ADD_PROTECTED_TOKEN_ROLE"
        )
        self.TRANSFER_ROLE = Permission(agent_app, "TRANSFER_ROLE")
        self.RUN_SCRIPT_ROLE = Permission(agent_app, "RUN_SCRIPT_ROLE")
        self.SAFE_EXECUTE_ROLE = Permission(agent_app, "SAFE_EXECUTE_ROLE")
        self.REMOVE_PROTECTED_TOKEN_ROLE = Permission(
            agent_app, "REMOVE_PROTECTED_TOKEN_ROLE"
        )
        self.DESIGNATE_SIGNER_ROLE = Permission(agent_app, "DESIGNATE_SIGNER_ROLE")
        self.EXECUTE_ROLE = Permission(agent_app, "EXECUTE_ROLE")
        self.ADD_PRESIGNED_HASH_ROLE = Permission(agent_app, "ADD_PRESIGNED_HASH_ROLE")


class LidoPermissions:
    def __init__(self, lido_app):
        self.PAUSE_ROLE = Permission(lido_app, "PAUSE_ROLE")
        self.RESUME_ROLE = Permission(lido_app, "RESUME_ROLE")
        self.STAKING_PAUSE_ROLE = Permission(lido_app, "STAKING_PAUSE_ROLE")
        self.STAKING_CONTROL_ROLE = Permission(lido_app, "STAKING_CONTROL_ROLE")

class NodeOperatorsRegistryPermissions:
    def __init__(self, node_operators_registry_app):
        self.STAKING_ROUTER_ROLE = Permission(
            node_operators_registry_app, "STAKING_ROUTER_ROLE"
        )
        self.MANAGE_NODE_OPERATOR_ROLE = Permission(
            node_operators_registry_app, "MANAGE_NODE_OPERATOR_ROLE"
        )
        self.MANAGE_SIGNING_KEYS = Permission(
            node_operators_registry_app, "MANAGE_SIGNING_KEYS"
        )
        self.SET_NODE_OPERATOR_LIMIT_ROLE = Permission(
            node_operators_registry_app, "SET_NODE_OPERATOR_LIMIT_ROLE"
        )



class TokenManagerPermissions:
    def __init__(self, token_manager_app):
        self.ISSUE_ROLE = Permission(token_manager_app, "ISSUE_ROLE")
        self.ASSIGN_ROLE = Permission(token_manager_app, "ASSIGN_ROLE")
        self.BURN_ROLE = Permission(token_manager_app, "BURN_ROLE")
        self.MINT_ROLE = Permission(token_manager_app, "MINT_ROLE")
        self.REVOKE_VESTINGS_ROLE = Permission(
            token_manager_app, "REVOKE_VESTINGS_ROLE"
        )


class VotingPermissions:
    def __init__(self, voting_app):
        self.MODIFY_QUORUM_ROLE = Permission(voting_app, "MODIFY_QUORUM_ROLE")
        self.MODIFY_SUPPORT_ROLE = Permission(voting_app, "MODIFY_SUPPORT_ROLE")
        self.CREATE_VOTES_ROLE = Permission(voting_app, "CREATE_VOTES_ROLE")


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
        return f"{self.app._name}.{self.role_name} ({self.role})"
