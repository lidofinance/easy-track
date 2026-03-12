# Curated Easy Track Exit Authorization Gap — Detailed Write-up

Line 1: Purpose
This document explains the authorization flaw in the Curated Easy Track exit factory, its exploit path, impact, and the precise fix. It is intentionally detailed and step-by-step for reviewers, auditors, and governance authors.

Line 5: Components in scope
- Easy Track EVMScript factory: contracts/EVMScriptFactories/CuratedSubmitExitRequestHashes.sol
- Shared validation library: contracts/libraries/SubmitExitRequestHashesUtils.sol
- Curated module registry: core/contracts/0.4.24/nos/NodeOperatorsRegistry.sol and core/contracts/0.4.24/lib/SigningKeys.sol
- Exit pipeline: core/contracts/0.8.9/oracle/ValidatorsExitBus.sol, TriggerableWithdrawalsGateway.sol, StakingRouter.sol, WithdrawalVaultEIP7002.sol

Line 11: Intended trust boundary
Easy Track factories are the only on-chain gatekeepers for privileged EVMScripts. Once a factory is whitelisted, the executor calls its target with elevated permissions. Therefore factory input validation must enforce ownership/authorization of the actions encoded in the EVMScript.

Line 15: Problem statement (high level)
The Curated exit factory authorizes motions using reward-address ownership and a mutable signing-key lookup. It does not require that the referenced key was ever deposited/used by that operator. A malicious Curated operator (or anyone with MANAGE_SIGNING_KEYS on that operator) can append arbitrary foreign pubkeys to their registry and craft exit motions that target other operators’ validators. The exit pipeline then queues EIP-7002 withdrawal requests for those foreign validators without subsequent ownership checks.

Line 21: Threat model
- Attacker capability: control the reward address of an active Curated node operator or possess a MANAGE_SIGNING_KEYS grant for that operator.
- Attacker cannot forge BLS signatures for foreign validators, cannot change withdrawal credentials (assumed Lido-controlled), but can append arbitrary pubkeys and signatures in the Curated registry.
- Defender expectation: only validators actually deposited by an operator can be exited via that operator’s privileged Easy Track motions.

Line 28: Preconditions for exploit
1) Attacker operator is active (reward address enabled) or attacker holds MANAGE_SIGNING_KEYS.
2) Victim validator has withdrawal credentials pointing to Lido withdrawal vault (normal for Curated).
3) Easy Track factory `CuratedSubmitExitRequestHashes` remains enabled.
4) Exit pipeline contracts are unpaused.

Line 35: Root cause in code (granular)
- In SubmitExitRequestHashesUtils.validateExitRequests:
  - call `_nodeOperatorsRegistry.getSigningKey(_input.nodeOpId, _input.valPubKeyIndex);`
  - destructured as `(bytes memory key, , )` meaning the third return value `bool used` is ignored.
  - validation compares `keccak256(key)` with provided pubkey hash; no check on `used`.
- In NodeOperatorsRegistry:
  - `addSigningKeys` allows an active reward address or MANAGE_SIGNING_KEYS grantee to append any 48-byte pubkey with any 96-byte signature.
  - `getSigningKey` returns `(key, depositSignature, used)` where `used` is true only after the key is consumed for an actual deposit/assignment.
- Because `used` is not enforced, “pubkey exists at index” becomes the only predicate, and that predicate is attacker-controlled.

Line 47: Exploit flow (A–F)
A) Inject foreign key
   - Attacker calls `addSigningKeys(attackerNodeOpId, 1, victimPubkey, garbageSig);`
   - Registry stores victim pubkey at new index; `used` remains false.
B) Craft Easy Track motion
   - Attacker prepares ExitRequestInput with nodeOpId = attackerNodeOpId, valPubKeyIndex = injected index, valIndex = victim validator index, valPubkey = victim pubkey.
   - Motion creator must equal attacker reward address; satisfied.
C) Motion enacted
   - After objection window, Easy Track executor calls ValidatorsExitBusOracle.submitExitRequestsHash with the hashed data produced by the factory.
D) Submit exit data (public)
   - Anyone submits packed exit data matching the hash via ValidatorsExitBus.submitExitRequestsData.
E) Trigger exits (public, fee-bearing)
   - Anyone calls ValidatorsExitBus.triggerExits; tuples passed forward are (moduleId, nodeOpId, pubkey). Note the valPubKeyIndex is gone.
F) Withdrawal request queued
   - TriggerableWithdrawalsGateway queues withdrawal requests in WithdrawalVaultEIP7002 by pubkey before module notification.
   - StakingRouter callback to Curated module does not verify ownership; failure is fail-open with queued request already added.

Line 70: Why `used` stops the exploit
- `used` is set only when a key is consumed for an actual validator deposit by that operator (via assignNextSigningKey and downstream deposit flow).
- Attacker cannot set `used=true` for a foreign pubkey without performing a real deposit that requires control of the corresponding private key/signature, which they lack.
- Therefore requiring `used` ensures only keys bound to real deposited validators of that operator can be referenced in exit motions.

Line 78: Impact details
- Forced full withdrawals or exits for other operators’ validators.
- Consumption of per-period exit limits in ValidatorsExitBus and TriggerableWithdrawalsGateway, delaying legitimate exits.
- Accounting confusion: ValidatorExitTriggered events will attribute the exit to the attacker operator id, misrepresenting responsibility.
- Potential slash-risk escalation if forced exits are timed badly, plus loss of future rewards for affected validators.

Line 86: Conditions where the flaw is benign
- If a validator does not have Lido withdrawal credentials, the queued EIP-7002 request would not be accepted by the consensus layer; however, Curated assumes Lido withdrawal credentials, so in practice most curated validators are vulnerable.
- If Easy Track is paused or the factory is removed, exploit is blocked; hence governance control is an effective temporary mitigation.

Line 93: Permanent fix (code change)
- Location: contracts/libraries/SubmitExitRequestHashesUtils.sol inside validateExitRequests, after fetching the signing key.
- Change: destructure and validate `used`.
- Pseudocode:
  ```
  (bytes memory key, , bool used) = _nodeOperatorsRegistry.getSigningKey(_input.nodeOpId, _input.valPubKeyIndex);
  require(used, ERROR_KEY_NOT_USED);
  require(keccak256(key) == providedPubkeyHash, ERROR_INVALID_PUBKEY);
  ```
- Add a dedicated error string constant `ERROR_KEY_NOT_USED` to maintain clarity.
- This preserves backward compatibility for legitimate exit requests, because they already reference deposited validators and therefore satisfy `used == true`.

Line 106: Immediate mitigation (governance)
- In the next voting round:
  - Disable or remove Curated exit factory permissions from Easy Track (revoke factory role or pause Easy Track motions targeting ValidatorsExitBusOracle.submitExitRequestsHash).
  - Optionally pause ValidatorsExitBus or TriggerableWithdrawalsGateway if rapid defense-in-depth is required.
- Rationale: prevents privileged hash creation while the code fix is prepared and deployed.

Line 114: Deployment plan
1) Draft and merge the `require(used)` patch in SubmitExitRequestHashesUtils with tests.
2) Deploy updated library and redeploy/upgrade factory if linking is required (depending on build setup).
3) Re-enable the Curated exit factory in Easy Track after the patched code is live.
4) Announce operational guidance to monitoring teams to expect `ERROR_KEY_NOT_USED` reverts for malformed motions.

Line 122: Testing strategy
- Unit tests in contracts/test/SubmitExitRequestHashesUtilsWrapper.sol:
  - New test: motion with unused key should revert with ERROR_KEY_NOT_USED.
  - Existing positive test with used key should still pass.
- Integration test:
  - Simulate operator adding arbitrary pubkey, creating motion, and ensure validation fails pre-hash.
- Fuzz test idea:
  - Random pubkey hashes paired with unused keys must fail; used keys with matching hash must pass.

Line 132: Backward compatibility considerations
- Legitimate exits reference validators that are already deposited; those keys are marked used, so no breakage.
- Motions referencing yet-to-be-deployed validators would fail, but such motions are nonsensical because exiting undeployed validators is not supported; this is acceptable and desirable.

Line 139: Residual risks after fix
- Requires correct propagation of the library change to all factories calling validateExitRequests (CuratedSubmitExitRequestHashes and SDVTSubmitExitRequestHashes). Ensure both use the same helper.
- If an operator somehow marks `used=true` for a foreign key via another bug, the check would be bypassed; no such path is known, but consider a quick audit of assignNextSigningKey and deposit flow.

Line 147: Governance recommendation text (short form)
- “Disable the Curated Easy Track exit EVMScript factory until the `require(used)` validation is deployed. Re-enable only after the patched helper is live.”

Line 151: Conclusion
The absence of `used` validation turns a mutable registry lookup into an authorization oracle. By enforcing `require(used)`, exit motions become bound to actually deposited validators of the specified operator, closing the privilege escalation vector. Immediate governance action can block exploitation until the fix is shipped.
