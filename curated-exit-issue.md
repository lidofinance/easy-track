# Curated Easy Track Exit Authorization Gap

## Summary
The Curated Easy Track factory `CuratedSubmitExitRequestHashes` plus helper `SubmitExitRequestHashesUtils` authorize exit motions by checking that the motion creator owns the node operator’s reward address and that the provided pubkey bytes match the key stored at a registry index. They **do not verify that the referenced signing key was ever deposited/used by that operator**. An active Curated operator (or anyone with its `MANAGE_SIGNING_KEYS` grant) can append arbitrary foreign pubkeys to their registry entries and craft exit motions that target other operators’ validators which use Lido-controlled withdrawal credentials. The exit pipeline then queues EIP‑7002 withdrawal requests for those foreign validators without module-side ownership checks.

## Impact
- Forced full withdrawals/exits for other Curated operators’ validators.
- Consumption of exit-rate limits in `ValidatorsExitBus` and `TriggerableWithdrawalsGateway`, causing operational disruption.
- Potential yield loss and validator set churn attributed to the malicious operator’s nodeOpId.

## Root Cause
`validateExitRequests` in `SubmitExitRequestHashesUtils` fetches `(key, , ) = getSigningKey(nodeOpId, valPubKeyIndex)` and only compares the raw pubkey bytes. It ignores the `used` flag, which distinguishes deposited/assigned keys from newly appended ones. Because `NodeOperatorsRegistry.addSigningKeys` allows an active reward address or `MANAGE_SIGNING_KEYS` grantee to append arbitrary pubkeys, “pubkey exists at index” is not a safe authorization predicate.

## Permanent Fix
Enforce that exit requests can reference only keys that were actually used for deposits by that operator:

- In `SubmitExitRequestHashesUtils.validateExitRequests`, read the third return value from `getSigningKey` and require it to be `true`.
  - Example: `(_, , bool used) = _nodeOperatorsRegistry.getSigningKey(...); require(used, ERROR_KEY_NOT_USED);`
- Keep existing pubkey equality check; this change is backward-compatible for legitimate exits because they already refer to deposited validators.

## Immediate Mitigation (Governance)
Until the on-chain fix is deployed:
- **Disable Curated Easy Track exit motions** in the next voting round (pause/remove `CuratedSubmitExitRequestHashes` factory permissions).
- Consider pausing related Easy Track permissions or rate-limit contracts if rapid response is needed.

## Recommended Sequence
1) Governance vote to disable Curated exit factory on Easy Track.  
2) Deploy patch adding `require(used)` in `SubmitExitRequestHashesUtils.validateExitRequests`.  
3) Re-enable the factory after the patched helper is live and integrated.  

## Rationale
The `used` flag cannot be set for a foreign pubkey without a real deposit under the attacker’s operator; therefore requiring it restores an immutable ownership proof and closes the authorization gap while leaving legitimate flows unaffected.
