# Foundry tests

Two suites, each on its own profile in `foundry.toml`:

| Suite | Profile | Compiles | Network |
|---|---|---|---|
| `unit/` | `unit` | `contracts/` and the tests at solc 0.8.6, so tests deploy the real contracts and stubs with `new` | none |
| `scenario/` | `default` | only `test/foundry`, with its own modern-pragma interfaces | a fork of hoodi or mainnet |

Plain `forge test` runs the default profile, so it runs the scenario suite only, and reports every
scenario contract as skipped when no RPC URL is set. The unit suite needs its profile:

```bash
npm run test:unit                  # FOUNDRY_PROFILE=unit forge test
CHAIN=hoodi npm run test:scenario  # forge test --match-path 'test/foundry/scenario/**'
```

`npm install` brings forge-std as a normal npm dependency, there is no submodule.

## Unit suite

Local tests of the Easy Track core and the libraries, ported from the Brownie suite in `tests/`,
one Foundry test per Python test. Every test deploys what it needs with `new` and runs
without a network. Stubs the tests share live in `unit/stubs/`, encoders and constants in
`unit/helpers/`.

```bash
npm run test:unit
FOUNDRY_PROFILE=unit forge test --match-contract EasyTrackTest   # one contract
```

## Scenario suite

Happy-path scenario tests for the **deployed** Easy Track EVM-script factories listed in
`deployed-{sr,sm}-<chain>.json`. Each test forks a live network and drives one factory through the
full motion lifecycle against the real on-chain contracts:

```
build the on-chain data the motion needs
createMotion (trustedCaller) → warp motionDuration → enactMotion → assert the on-chain effect
```

The suite prepares only **data**: operators, penalties, slashings, groups. Everything else must
already hold on-chain: the factory registered in Easy Track with permissions, the executor holding
the roles the motion calls, and the contracts the factory targets at the expected version. If any of
that is missing, the test **fails**. It is never auto-arranged. The suite is independent of the
Brownie suite and has no Python.

### Running

`forge` / `just` auto-load `.env`, which holds `HOODI_RPC_URL` / `MAINNET_RPC_URL`. `CHAIN`,
default `hoodi`, selects the network and the `deployed-*.json` files. `RPC_URL` is not consulted.

```bash
CHAIN=hoodi   npm run test:scenario
CHAIN=mainnet npm run test:scenario
CHAIN=hoodi   forge test --mc SettleGeneralDelayedPenalty -vvv   # one factory
```

A root [`justfile`](../../justfile) has two recipes:

```bash
RPC_URL=$MAINNET_RPC_URL just make-fork                             # start a local Anvil fork (reused if up)
CHAIN=mainnet just test-scenario --fork-url http://127.0.0.1:8545  # run against it (fast, cached)
just test-scenario                                                 # or self-fork <CHAIN>_RPC_URL
```

If the Easy Track contract is already present in the running EVM, as with `--fork-url`, the suite
reuses that fork instead of re-forking. With no RPC and no active fork every scenario contract is
reported as `[SKIP] setUp()` with the name of the variable it looked for. Forge keeps every state
change in memory, so a reused Anvil fork is left untouched.

### Coverage

Every deployed factory is covered. Preconditions are **constructed** on the fork through module
admin roles. Nothing scans for pre-existing state.

| Factory (`deployed-*.json` key) | Test | Scenarios |
|---|---|---|
| `UpdateStakingModuleShareLimits:CSM` (sr) | `sr/UpdateStakingModuleShareLimits.t.sol` | increase / decrease the limits. Reject a stale committed current value |
| `AllowConsolidationPair` (sr) | `sr/AllowConsolidationPair.t.sol` | allow a source+target pair linked in one MetaRegistry group. Update its submitter |
| `SettleGeneralDelayedPenalty:CSM/CM` (sm) | `sm/SettleGeneralDelayedPenalty.t.sol` | settle one / multiple locked penalties. Reject nothing-to-settle, an already-settled lock or a stale nonce |
| `SetMerkleGateTree:CSM/CM` (sm) | `sm/SetMerkleGateTree.t.sol` | update a gate's tree. Reject a stale committed current tree |
| `ReportWithdrawalsForSlashedValidators:CSM/CM` (sm) | `sm/ReportWithdrawalsForSlashedValidators.t.sol` | report a slashed validator withdrawn, and again as a no-op. Reject a zero penalty or zero exit balance |
| `CreateOrUpdateOperatorGroup:CM` (sm) | `sm/CreateOrUpdateOperatorGroup.t.sol` | create a group. Update it to non-empty / empty / empty→empty. Reject a stale committed group |

### Notes

- **Only data is arranged.** The suite does not register factories, grant the executor its roles or
  upgrade protocol contracts. Those must already hold on-chain, else the test fails. Role grants
  exist only to build the data preconditions above.
- **Interfaces** in `interfaces/{External,Factories,EasyTrack}.sol` are self-contained with a modern
  pragma, so the suite never compiles `contracts/`. Build the factories with the separate profile:
  `FOUNDRY_PROFILE=contracts forge build`.
- **Gate discovery.** The gate of `SetMerkleGateTree` is the module's `CREATE_NODE_OPERATOR_ROLE`
  holder the executor may set the tree on. The staking-module addresses live in `NetworkConfig`.
  Every other target comes from the factory getters at runtime.
- **Commit re-validation.** Factories that commit a current value at creation, the share limits, the
  gate tree, the operator group and the lock nonce, re-check it at enactment. Each has a test that
  mutates that value after `createMotion` and asserts `enactMotion` then reverts.
