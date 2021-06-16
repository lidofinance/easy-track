## EasyTracksRegistry

Contains logic to control list of active easy tracks. Only Lido DAO has rights to change list of easy tracks.

### Methods

#### function addEasyTrack(address \_easyTrack)

Adds a new `_easyTrack` into the current list of easy tracks. Can only be called by DAO upon Aragon voting.

#### function deleteEasyTrack(address \_easyTrack)

Removes easy track with `_easyTrack` address from the list of easy tracks. If an executor was not found throws the `"EASY_TRACK_NOT_FOUND"` error. Can only be called by DAO upon Aragon voting.

#### function isEasyTrack(address \_maybeEasyTrack)

Returns if a `_maybeEasyTrack` is in the list of easy tracks.

#### function getEasyTracks()

Returns array of active easy tracks in the registry.

## EvmScriptExecutor

Contains logic to create and execute aragon evm scripts via forwarding to Aragon's agent.
Method to execute script marked as internal and can be called only by inherited contract.

## MotionsRegistry

Stores list of active motions and methods to create, cancel, object and enact motions. Only addresses contained in `EasyTracksRegistry` can create, cancel and enact motions. Method object can be called by LDO holders. Inherits `EvmScriptRunner` and has permission to forward to Aragon's agent. Motion data is stored in the following struct:

```solidity=
struct Motion {
    uint256 id;
    address executor;
    uint256 duration;
    uint256 startDate;
    uint256 snapshotBlock;
    uint256 objectionsThreshold;
    uint256 objectionsAmount;
    uint256 objectionsAmountPct;
    bytes data;
}
```

Due to various types of motion data, it is stored as bytes; and in easy track contracts, it can be decoded to use actual values.

### Methods

#### function setMotionDuration(uint256 \_motionDuration)

Sets the duration of newly created motions. Minimum value is 48 hours. The motion can only be enacted after this time in case the objections threshold has not been exceeded. Can only be called by the contract owner.

Events:

```solidity=
event MotionDurationChanged(uint256 _newDuration)
```

#### function setObjectionsThreshold(uint256 \_objectionsThreshold)

Sets new `objectionsThreshold` value. Maximum value is 5%. Can only be called by the contract owner.

Events:

```solidity=
event ObjectionsThresholdChanged(uint256 _newThreshold)
```

#### function setMotionsCountLimit(uint256 \_motionsLimit)

Sets new value for `motionsCountLimit`. Max value limitted by the `MAX_MOTIONS_COUNT_LIMIT` constant. Can only be called by the contract owner.

Events:

```solidity=
event MotionsCountLimitChanged(
    uint256 _newMotionsCountLimit
)
```

#### function objectToMotion(uint256 \_motionId)

Submits an objection from LDO token holder. The objection power equals the amount of tokens held. Since LDO is MiniMeToken, it utilizes `balanceOfAt` and `totalSupplyAt` methods to prevent multiple objections submitted with the same tokens. If `objectionsThreshold` has been exceeded, the motion will be deleted and `MotionRejected` event will be emitted.

Events:

```solidity=
event ObjectionSent(
    uint256 indexed _motionId,
    address indexed _voterAddress,
    uint256 _weight,
    uint256 _votingPower
)
event MotionRejected(uint256 indexed _motionId)
```

#### function getMotions()

Returns list of motions not enacted and not canceled yet.

#### function getMotionData(uint256 \_motionId)

Returns motion data encoded as `bytes`.

#### function canObjectToMotion(uint256 \_motionId, address \_objector)

Returns if a user can submit an objection or not.

#### function createMotion(bytes memory \_data)

Method creates a new `Motion` and saves it into the respective mapping. Method accepts calls only from addresses listed in `EasyTracksRegistry`. Validates that count of active motions is less that `motionsCountLimit`. Returns id of created motion.

Events:

```solidity=
event MotionCreated(
    uint256 indexed _motionId,
    uint256 indexed _executorId,
    bytes data
)
```

#### function cancelMotion(uint256 \_motionId)

Method removes motion entity. Accepts calls only from addresses listed in `EasyTracksRegistry`. Validates that `msg.sender` is equal to `motions.easyTrack`.

Events:

```solidity=
event MotionCanceled(uint256 indexed _motionId)
```

#### function enactMotion(uint256 \_motionId, bytes memory \_evmScript)

Method marks motion as enacted. Accepts calls only from addresses listed in `EasyTracksRegistry`. Validates that `msg.sender` is equal to `motions.easyTrack`.
If `_evmScript` is not empty, will forward it as aragon EVM script to the Aragon Agent. After that, method deletes the motion from the corresponding mapping.

Method also has overloaded variant **`function enactMotion(uint256 _motionId) external`** which passes empty evm script `_evmScript` value.

Events:

```solidity=
event MotionEnacted(uint256 indexed _motionId)
```

## NodeOperatorsEasyTrack

Allows create, cancel and enact motions to increase node operator's staking limits.

### function createMotion(uint256 \_nodeOperatorId, uint256 \_stakingLimit)

Creates motion to set staking limit equals to `_stakingLimit` on node operator with id `_nodeOperatorId`. Before creation makes next checks:

- Requires the node operator to not be disabled.
- Requires the withdrawl address of the node operator to match the address of `_caller`.
- Requires the new value of `_stakingLimit` to be greater than the current value and less than or equal to the number of total signing keys of the node operator.

### function cancelMotion(uint256 \_motionId, uint256 \_nodeOperatorId)

Cancels motion with given id. To cancel motion requires that withdrawal address of node operator with id `_nodeOperatorId` is equal to `msg.sender`.

### function enactMotion(uint256 \_motionId)

Enacts passed motion and generates evm script to set new staking limit for node operator. Generated script is passed to `MotionsRegistry` to be executed. Before enact runs next checks:

- Requires the node operator to not be disabled.
- Requires the new value of `_stakingLimit` to be greater than the current value and less than or equal to the number of total signing keys of the node operator.

## LegoEasyTrack

Allows create, cancel and enact motions to allocate ERC20 tokens or ETH for LEGO grants.

### function createMotion(address[] memory \_rewardTokens, uint256[] memory \_amounts)

Creates motion to transfer to LEGO program address tokens listed in `_rewardTokens` with corresponding amount in `_amounts`. `address(0)` means ETH. Accept calls only from specified address. Zero payments forbidden.

### function cancelMotion(uint256 \_motionId)

Cancels motion with given id. Accept calls only from specified address.

### function enactMotion(uint256 \_motionId)

Enacts motion and generates evm script to run transfers of tokens listed in motion's data with specified amounts. Generated script is passed to `MotionsRegistry` to be executed. Validates that data is valid before enacting.

## TopUpRewardProgramEasyTrack

Allows create, enact and cancel motions to transfer LDO into one or multiple allowed recipients.

### Methods

#### function initialize(address \_addRewardProgramEasyTrack, address \_removeRewardProgramEasyTrack)

Sets values for `addRewardProgramEasyTrack` and `removeRewardProgramEasyTrack` variables if they haven't set yet. Throws `"ALREADY_INITIALIZED"` in other cases.

#### function addRewardProgram(address \_rewardProgram)

Adds reward program address to `rewardPrograms` if it hasn't added yet, throws `"REWARD_PROGRAM_ALREADY_ADDED"` in other cases. Might be called only by `AddRewardProgramEasyTrack` contract.

#### function removeRewardProgram(address \_rewardProgram)

Removes reward program address from `rewardPrograms`. Throws `"REWARD_PROGRAM_NOT_FOUND"` if program address not in array. Might be called only by `RemoveRewardProgramEasyTrack` contract.

#### function isAllowed(address \_rewardProgram)

Shows if address is whitelisted in `rewardPrograms`.

#### function createMotion(address[] memory \_rewardPrograms, uint256[] memory \_amounts)

Creates motion to transfer LDO to each address in `_rewardPrograms`. Amount of transfer contained in `_amounts`. Checks if an each address in `_recipients` array contained in list of allowed reward programs. Zero transfers forbidden. The method might be called only by specified trusted address, set on deploy.

#### function cancelMotion(uint256 \_motionId)

Cancels motion with given id. Accept calls only from specified trusted address address.

#### function enactMotion(uint256 \_motionId)

Enacts motion and generates script to run transfers of LDO to addresses listed in motion's data with specified amounts. Generated script is passed to `MotionsRegistry` to be executed.Validates that data is valid before enacting.

## AddRewardProgramEasyTrack

Allows create, enact and cancel motions to add new reward program to the list of allowed LDO recipients.

#### function createMotion(address \_rewardProgram)

Creates motion to add new reward program to the list of allowed LDO recipients. Checks if an `_rewardProgram` hasn't whitelisted yet and throws `REWARD_PROGRAM_ALREADY_ADDED` in other case. The method might be called only by specified trusted address, set on deploy.

#### function cancelMotion(uint256 \_motionId)

Cancels motion with given id. Accept calls only from specified trusted address.

#### function enactMotion(uint256 \_motionId)

Enacts motion and calls `TopUpRewardProgramEasyTrack.addRewardProgram`. Validates that data is valid before enacting.

## RemoveRewardProgramEasyTrack

Allows create, enact and cancel motions to delete reward program from the list of allowed LDO recipients.

#### function createMotion(address \_rewardProgram)

Creates motion to delete reward program from the list of allowed LDO recipients. Checks if an `_rewardProgram` is in whitelist and throws `REWARD_PROGRAM_NOT_FOUND` in other case. The method might be called only by specified trusted address, set on deploy.

#### function cancelMotion(uint256 \_motionId)

Cancels motion with given id. Accept calls only from specified trusted address.

#### function enactMotion(uint256 \_motionId)

Enacts motion and calls `TopUpRewardProgramEasyTrack.removeRewardProgram`. Validates that data is valid before enacting.
