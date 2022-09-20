# Easy Track

## Problem

Lido DAO governance currently relies on Aragon voting model. This means DAO approves or rejects proposals via direct governance token voting. Though transparent and reliable, it is not a convenient way to make decisions only affecting small groups of Lido DAO members. Besides, direct token voting doesn't exactly reflect all the decision making processes within the Lido DAO and is often used only to rubber-stamp an existing consensus.
There are a few natural sub-governance groups within the DAO, e.g. validators committee, financial operations team and LEGO committee. Every day they need to take routine actions only related to their field of expertise. The decisions they make hardly ever spark any debate in the community, and votings on such decisions often struggle to attract wider DAO attention and thus, to pass.

## Solution

Easy Track frictionless motions are solution to this problem.
Easy Track motion is a lightweight voting considered to have passed if the minimum objections threshold hasn’t been exceeded. As opposed to traditional Aragon votings, Easy Track motions are cheaper (no need to vote ‘pro’, token holders only have to vote ‘contra’ if they have objections) and easier to manage (no need to ask broad DAO community vote on proposals sparking no debate).

## Use cases for Easy Track motions

There are four types of votings run periodically by the Lido DAO that are proposed to be wrapped into the new Easy Track motions.

- Node Operators increasing staking limits
- Funds being allocated into reward programs
- Funds being allocated to LEGO program
- Funds being allocated to the whitelisted referral partners

See [specification.md](https://github.com/lidofinance/easy-track/blob/master/specification.md) for full specification.

## EVMScript Factory Requirements

### Methods Compatibility

**Every EVMScript factory must implement [`IEVMScriptFactory`](https://github.com/lidofinance/easy-track/blob/master/contracts/interfaces/IEVMScriptFactory.sol) interface.**

Methods from this interface are used by EasyTrack at the motion lifecycle.

### Accessibility For Aragon Voting

**Every action done by EasyTrack must be allowed to do also by Aragon Voting.**

This requirement fills automatically in cases when easy tracks do actions provided by the Aragon application. But for contracts outside the Aragon ecosystem access to Voting must be provided explicitly. To grant such access you can use role-based control access contracts from the OpenZeppelin package. To see an example of how this pattern was used in EVMScript factories see the `RewardProgramsRegistry.sol` contract.

### Onchain EVMScript calldata decoding

**Each EVMScript factory must provide the method `decodeEVMScriptCallData` to decode the calldata used in it.**

This provides a flexible way to check which parameters were used to create motion even without access to UI.

### Carefully review added factories

**Each EVMScript factory must be carefully reviewed and tested before adding to the EasyTrack.**

Remember, that EVMScript generated by the factory might be run with potentially dangerous permissions. Be sure, that generated EVMScript makes exactly what it has to do.

### Choose the narrowest set of permissions

**When adds new EVMScript factory use only required permissions**

Permissions for EVMScript factory must contain only methods used by generated EVMScript.

## Project Setup

To use the tools that this project provides, please pull the repository from GitHub and install its dependencies as follows. It is recommended to use a Python virtual environment.

```bash
git clone https://github.com/lidofinance/easy-track
cd easy-track
yarn install
poetry install
poetry run brownie networks import network-config.yaml True
poetry shell
```


Compile the Smart Contracts:

```bash
brownie compile # add `--size` to see contract compiled sizes
```

## Scripts

### `deploy.py`

Contains script to deploy main Easy Track contracts with EVM Script factories.
Script requires next ENV variables to be set:

- `DEPLOYER` - id of brownie's account which will deploy contracts. Might be skipped if run on `development` network.
- `LEGO_PROGRAM_VAULT` - address of Lido's LEGO program
- `LEGO_COMMITTEE_MULTISIG` - address allowed to create motions to top up LEGO program
- `REWARD_PROGRAMS_MULTISIG` - address allowed to create motions to add, remove or top up reward program
- `PAUSE_ADDRESS` - address to grant PAUSE_ROLE

Next optional variables can be set:

- `UNPAUSE_ADDRESS` - address to grant UNPAUSE_ROLE
- `CANCEL_ADDRESS` - address to grant CANCEL_ROLE

### `final_check.py`

Contains script to validate deployed setup of EasyTrack in mainnet network.

Script accepts next optional ENV variables:

- `GRANT_PERMISSIONS_VOTING_ID` - id of voting where permissions `CREATE_PAYMENTS_ROLE` and `SET_NODE_OPERATOR_LIMIT_ROLE` granted to `EVMScriptExecutor`. If this variable is passed, the simulation will not create new voting to add permissions to `EVMScriptExecutor`.

### `grant_executor_permissions.py`

Creates Aragon's Voting to grants permissions to EVMScriptExecutor required to execute EVMScripts generated by EVMScript factories. After voting creation checks that after execution all permissions will be granted correctly.

Script requires next ENV variables to be set:

- `DEPLOYER` - id of brownie's account which will deploy contracts. To create a voting account must have LDO Tokens. Might be skipped if run on a `development` network.
- `EVM_SCRIPT_EXECUTOR` - address to grant permissions.

### `revoke_all_permissions.py`

Creates Aragon's Voting to revoke all granted permissions from EVMScriptExecutor. After voting creation checks that after execution EVMScriptExecutor will has no any permissions.

Script requires next ENV variables to be set:

- `DEPLOYER` - id of brownie's account which will deploy contracts. To create a voting account must have LDO Tokens. Might be skipped if run on a `development` network.
- `EVM_SCRIPT_EXECUTOR` - address to grant permissions.

### `renounce_all_roles.py`

Sends transactions to renounce `DEFAULT_ADMIN_ROLE`, `PAUSE_ROLE`, `UNPAUSE_ROLE`, `CANCEL_ROLE` roles from EasyTrack contract deployed in mainnet [`0xF0211b7660680B49De1A7E9f25C65660F0a13Fea`](https://etherscan.io/address/0xf0211b7660680b49de1a7e9f25c65660f0a13fea).

Script requires next ENV variables to be set:

- `DEPLOYER` - address of the account that renounces roles

## Tests

The fastest way to run the tests is:

```bash
brownie test
```

Run tests with coverage and gas profiling:

```bash
brownie test --coverage --gas
```

#### Coverage notes

Current brownie version has problems with coverage reports for some contracts. Contracts which use `immutable` variables don't get on the resulting report. Details can be found in this [issue](https://github.com/eth-brownie/brownie/issues/1087). Easy Track uses `immutable` modifier in next contracts:

- [TrustedCaller.sol](https://github.com/lidofinance/easy-track/blob/a72858804481009f2e09508ffbf93d8a4aee6c84/contracts/TrustedCaller.sol#L9)
- [EVMScriptExecutor.sol](https://github.com/lidofinance/easy-track/blob/a72858804481009f2e09508ffbf93d8a4aee6c84/contracts/EvmScriptExecutor.sol#L39)
- [AddRewardProgram.sol](https://github.com/lidofinance/easy-track/blob/a72858804481009f2e09508ffbf93d8a4aee6c84/contracts/EVMScriptFactories/AddRewardProgram.sol#L24)
- [IncreaseNodeOperatorStakingLimit.sol](https://github.com/lidofinance/easy-track/blob/a72858804481009f2e09508ffbf93d8a4aee6c84/contracts/EVMScriptFactories/IncreaseNodeOperatorStakingLimit.sol#L50)
- [RemoveRewardProgram.sol](https://github.com/lidofinance/easy-track/blob/a72858804481009f2e09508ffbf93d8a4aee6c84/contracts/EVMScriptFactories/RemoveRewardProgram.sol#L23)
- [TopUpLegoProgram.sol](https://github.com/lidofinance/easy-track/blob/a72858804481009f2e09508ffbf93d8a4aee6c84/contracts/EVMScriptFactories/TopUpLegoProgram.sol#L26)
- [TopUpRewardProgram.sol](https://github.com/lidofinance/easy-track/blob/a72858804481009f2e09508ffbf93d8a4aee6c84/contracts/EVMScriptFactories/TopUpRewardPrograms.sol#L27)
- [TopUpAllowedRecipients.sol](https://github.com/lidofinance/easy-track/blob/522ae893f6c03516354a8d1950b29b3203adae52/contracts/EVMScriptFactories/TopUpAllowedRecipients.sol#L29)

The workaround for the coverage problem is removing the `immutable` modifier from the above contracts. Without modifier above contracts will be listed in the coverage report
