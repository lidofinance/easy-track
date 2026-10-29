# The Brownie to Foundry port

The Foundry suites under `test/foundry` are a port of the Brownie suite under `tests/`, one Foundry test per Python test, or one per case of a parametrized test. The Brownie suite stays as it is and keeps running in CI. This file records where each Python file went, what the port replaced and where the two suites differ.

## Where the Python files went

| Brownie | Foundry |
|---|---|
| `tests/test_*.py` of the core contracts: Easy Track, the executor, the factories registry, motion settings, the trusted caller, the reward programs and allowed recipients registries | `unit/<Contract>.t.sol` |
| `tests/libraries/` | `unit/libraries/` |
| `tests/evm_script_factories/` | `unit/factories/`, the vault factories under `unit/factories/vaultFactories/` |
| `tests/payouts/` | `unit/payouts/` |
| `tests/test_bokky_poo_bahs_date-time-library.py` | `unit/BokkyPooBahsDateTimeLibrary.t.sol`, see the date-time section |
| `tests/test_aragon_acl.py` | `scenario/aragon/AragonACL.t.sol` |
| `tests/test_reward_programs.py`, `tests/integration/test_reward_programs_happy_path.py`, the same flow under two titles | `scenario/aragon/RewardProgramsEasyTrack.t.sol` |
| `tests/integration/test_lego_happy_path.py` | `scenario/aragon/LegoProgramEasyTrack.t.sol` |
| `tests/integration/test_node_operators_easy_track.py` | `scenario/aragon/NodeOperatorsEasyTrack.t.sol` |
| `tests/integration/payouts/` | `scenario/payouts/` |
| `tests/integration/test_*_submit_exit_request_hashes_happy_path.py` | `scenario/vebo/` |
| `tests/integration/test_mev_boost_relays_allowed_list_happy_path.py` | `scenario/mevboost/` |
| `tests/integration/test_operator_grid_happy_path.py`, `test_vault_hub_happy_path.py` | `scenario/vaults/` |
| `tests/integration/test_set_deposits_reserve_target_happy_path.py` | `scenario/lido/SetDepositsReserveTargetFreshFactory.t.sol` |
| `tests/scenario/test_set_deposits_reserve_target_scenario.py` | `scenario/lido/SetDepositsReserveTarget.t.sol` |
| `tests/scenario/test_dvt_*.py` | `scenario/sdvt/` |
| `tests/scenario/*_scenario.py` of the staking router and staking module factories | `scenario/sr/`, `scenario/sm/` |
| `tests/scripts/` | `scenario/aragon/DeployScript.t.sol`, `scenario/aragon/ExecutorPermissions.t.sol`, see the scripts section |

Not ported: `tests/test_vote_for_reward_programs.py`. Brownie skips it unconditionally, and it checks a vote started by a Python script rather than the contracts.

Added: two Python tests are defined twice in their modules, so pytest collects only the second and never runs the first. The port restores both under their own names, the stranger who may not set the date-time contract in `unit/AllowedRecipientsRegistry.t.sol` and the token removed while a top-up motion is in flight in `scenario/payouts/AllowedRecipientsMotionsMultiToken.t.sol`.

## Network

Brownie runs the whole suite on a mainnet fork, the unit tests included, and takes LDO, Voting, the Agent, Finance, the ACL, CallsScript and the date-time contract from the fork. The port splits the suite in two.

The unit suite runs with no network. Stand-ins under `unit/stubs/` replace the fork contracts the core tests depend on:

- `MiniMeTokenStub` for LDO. Its snapshot getters return the live balances, which holds because the unit tests never move tokens after a motion is created.
- `CallsScriptStub` for the aragonOS CallsScript the executor delegatecalls into. It keeps the initialization-block guard, the call loop and the revert forwarding.
- `ACLStub` for the aragonOS ACL the node operator factories read. It keeps the permission store with its parameters and has no permission manager.
- `BokkyPooBahsDateTimeContract` for the deployed date-time contract the limits checker reads.

Voting, the Agent and Finance are plain addresses. The stubs under `contracts/test/` are reused as the Python fixtures used them. The EIP-7002 withdrawal request fee of `ForceValidatorExitsInVaultHub` is a `vm.mockCall` on the predeploy address, nothing is etched there. The port added two constants and the `getNodeOperatorIsActive` getter to `NodeOperatorsRegistryStub`, the only change under `contracts/`.

The scenario suite forks a live network. It defaults to Hoodi, where CI runs it, and supports mainnet. Without an RPC URL it skips every contract where Brownie would fail.

## The date-time library test

The Python test checks the mainnet date-time contract against Python's `datetime`. The Foundry test checks the stub against `unit/helpers/Calendar.sol`, a reference calendar that counts days year by year and month by month and shares no arithmetic with the stub. It protects the stub the payouts unit tests deploy and says nothing about the deployed contract.

## Two compilers

The contracts under `contracts/` compile at solc 0.8.6 and stay byte for byte as deployed. The unit suite compiles with them and deploys everything with `new`, which pins forge-std at v1.9.6, a release that still compiles at 0.8.6. Two consequences in the tests: events are redeclared, since 0.8.6 cannot emit another contract's events, and the access control revert reasons spell the account in lowercase, as OpenZeppelin v4 does.

The scenario suite compiles at solc 0.8.38 and never compiles `contracts/`. It calls the deployed contracts through the self-contained interfaces under `interfaces/`, and deploys fresh factories, stubs and Easy Tracks from the `out/` artifacts of `forge build` with `deployCode`. The build therefore precedes every scenario run.

## DAO votes

Brownie passes real votes: a Voting vote submits dual governance proposals and `utils/dual_governance.py` drives them through the timelock. The port replays the effect of a vote instead:

- A vote that runs a script through the executor: Voting points the executor at the Agent with `setEasyTrack`, the Agent executes the script, Voting points it back.
- A vote that only grants an Aragon permission: the grant from the permission's manager.
- The payouts vote and the vote adding a curated operator: the Agent's call. The MEV-Boost vote: the list owner's `set_manager`.

The permission scripts' votes are real: the scripts open them through the TokenManager, the test passes them with LDO minted as the token's controller and executes them through Voting, after a setup vote hands Voting the manager slot of each role. The dual governance timelock is never driven.

## Deployed and fresh factories

The scenario suite drives a deployed factory as the DAO registered it and leaves the executor's protocol roles as they are on-chain. The tests build their data preconditions through module admin roles and scan for no pre-existing state. Where the fork lacks what a Brownie fixture set up, the test does what a vote would: registers the deployed exit request and MEV-Boost factories as Voting, re-registers `SetMerkleGateTree` with a stub gate, registers a second `UpdateStakingModuleShareLimits` for the missing module case, deploys its own Easy Track for the reward programs, LEGO program, staking limit, vaults and script suites, and regrants the payouts executor `CREATE_PAYMENTS_ROLE` on Finance without parameters, as the Brownie fixtures do.

A suite skips a chain that cannot host it: the SimpleDVT suites where `IncreaseVettedValidatorsLimit` is deployed but not registered, as on mainnet, the vaults suites without the vaults contracts, the deposits reserve target suites without the factory or without the target on Lido.

## Scripts

`tests/scripts/` tests the Python deploy and permission scripts. The Foundry counterparts run the Foundry scripts under `script/` on the fork, with the script contract as the deployer. The Python scripts are covered by the Brownie suite only.

## Test shape

- Brownie shares module-scoped fixtures and chain snapshots across tests. Foundry runs `setUp` per test, so a Python file whose tests build on the state earlier tests left became one test function running the sequence, as in `scenario/sdvt/SimpleDvtLifecycle.t.sol` and `SimpleDvtCollisions.t.sol`.
- A parametrized Python test became one Foundry test per case, named after the case, or a loop over the cases where they span a range. A file parametrized over modules or instances became an abstract contract with one concrete contract per variant: CSM and CM under `scenario/sm/`, Curated and SDVT in `unit/factories/SubmitExitRequestHashes.t.sol`, one per instance of `integration-test-addresses-<chain>.yaml` under `scenario/payouts/`.
- A payouts motions contract binds its instance by name and skips when the chain's file lacks it, as pytest would collect none. A contract the file lists as `"local"` or omits is deployed fresh. On a chain without the file a `Default` contract deploys everything fresh. The happy-path files run once, their Python ids repeat per instance but the instance plays no part. `helpers/IntegrationTestAddresses.sol` reads the file line by line, since forge parses JSON and TOML but not YAML.
- A stETH payout is checked within 2 wei per recipient, the rounding a stETH transfer may lose, and in shares as well.
- Calendar periods of the payouts registries are computed through the deployed date-time contract, so the tests warp to period boundaries where Brownie sleeps by a duration.
- Brownie reads a revert reason it cannot match through a hardhat workaround in ten files. The port expects the same reason with a plain `vm.expectRevert`.
- Names: `test_create_evm_script` became `test_CreatesEVMScript`, `test_deploy` became `test_SetsInitialState`, failure tests `test_RevertWhen_<Condition>`, forking tests `testFork_<Description>`. Helpers are named by their action.

## Formatting

`test/foundry` and `script` are formatted with `forge fmt` and excluded from prettier. `contracts/` is excluded from `forge fmt` and `forge lint`, since the deployed sources must not change.
