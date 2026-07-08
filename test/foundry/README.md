# Foundry fork scenario tests (deployed sr/sm factories)

Happy-path scenario tests for the **deployed** EasyTrack EVM-script factories listed in
`deployed-{sr,sm}-<chain>.json`. Each test forks a live network and drives one factory through the
full motion lifecycle against the real on-chain contracts:

```
build the on-chain data the motion needs
createMotion (trustedCaller) → warp motionDuration → enactMotion → assert the on-chain effect
```

The suite prepares only **data** (operators, penalties, slashings, groups). Everything else must
already hold on-chain: the factory registered in EasyTrack with permissions, the executor holding the
roles the motion calls, and the contracts the factory targets at the expected version. If any of that
is missing, the test **fails** — it is never auto-arranged. Independent of the Brownie suite (no Python).

## Running

`npm install` (forge-std is a normal npm dep — no submodule). `forge` / `just` auto-load `.env`
(`HOODI_RPC_URL` / `MAINNET_RPC_URL`). `CHAIN` (default `hoodi`) selects the network + `deployed-*.json`.

```bash
CHAIN=hoodi   forge test -vv
CHAIN=mainnet forge test -vv
CHAIN=hoodi   forge test --mc SettleGeneralDelayedPenalty -vvv   # one factory
```

A root [`justfile`](../../justfile) has two recipes:

```bash
RPC_URL=$MAINNET_RPC_URL just make-fork                             # start a local Anvil fork (reused if up)
CHAIN=mainnet just test-scenario --fork-url http://127.0.0.1:8545  # run against it (fast, cached)
just test-scenario                                                 # or self-fork <CHAIN>_RPC_URL
```

If the EasyTrack contract is already present in the running EVM (e.g. `--fork-url`), the suite reuses
that fork instead of re-forking; with no RPC and no active fork it is skipped. Each test
snapshots/reverts (`vm.snapshotState` / `vm.revertToState`), leaving a reused fork unspoiled.

## Coverage

One test per deployed factory. Every precondition is **constructed** on the fork (no scanning for
pre-existing state) via module admin roles.

| Factory (deployed-*.json key) | Test | Precondition |
|---|---|---|
| `UpdateStakingModuleShareLimits:CSM` (sr) | `sr/UpdateStakingModuleShareLimits.t.sol` | — |
| `AllowConsolidationPair` (sr) | `sr/AllowConsolidationPair.t.sol` | a source + target operator in one MetaRegistry group |
| `SettleGeneralDelayedPenalty:CSM/CM` (sm) | `sm/SettleGeneralDelayedPenalty.t.sol` | a bonded operator with a locked penalty |
| `SetMerkleGateTree:CSM/CM` (sm) | `sm/SetMerkleGateTree.t.sol` | — |
| `ReportWithdrawalsForSlashedValidators:CSM/CM` (sm) | `sm/ReportWithdrawalsForSlashedValidators.t.sol` | a deposited operator, marked slashed |
| `CreateOrUpdateOperatorGroup:CM` (sm) | `sm/CreateOrUpdateOperatorGroup.t.sol` | a fresh (ungrouped) sub + external operator |

## Notes

- **Only data is arranged.** The suite does not register factories, grant the executor its roles, or
  upgrade protocol contracts; those must already hold on-chain, else the test fails. Role grants exist
  only to build the data preconditions above.
- **Interfaces** (`interfaces/{External,Factories,EasyTrack}.sol`) are self-contained (modern pragma) so
  the suite never compiles `contracts/`. Build/deploy the factories with the separate profile:
  `FOUNDRY_PROFILE=contracts forge build`.
- **Gate discovery.** `SetMerkleGateTree`'s gate is the module's
  `CREATE_NODE_OPERATOR_ROLE` holder the executor may set the tree on. The staking-module addresses live
  in `_networkConfig`; every other target comes from the factory getters at runtime.
```
