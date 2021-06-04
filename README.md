## EasyTrackRegistry

### Abstract

`EasyTrackRegistry` is the main contract containing all required logic to manage motions, except for permission checks to create/cancel motions and enacting logic specific for each easy track. 
Series of standalone contracts define the further easy track logic. These contracts implement `IEasyTrackExecutor` interface and can be added into the registry by DAO via Aragon voting. 
`EasyTrackRegistry` inherits from `Ownable` contract from `OpenZeppelin` package and restricts access to some methods to the Lido DAO only.

### Storage Variables

Motion data is stored in the following struct:

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

Due to various types of motion data, it is stored as bytes; and in derived contracts, it can be decoded to use actual values. All motions are stored in the contract as array:

```solidity=
Motion[] public motions;
uint256 private lastMotionId;
mapping(uint256 => uint256) motionIndicesByMotionId;
```

Motion's objections stored in standalone mapping:

```solidity=
mapping(uint256 => mapping(address => bool)) objections;
```

To keep a flexible way of adding new motion types in the future, easy track stores logic for specific motions in standalone contracts. These contracts have to implement `IEasyTrackExecutor` interface:

```solidity=
interface IEasyTrackExecutor {
    function beforeCreateMotionGuard(
        address _caller,
        bytes memory _data
    ) external;

    function beforeCancelMotionGuard(
        address _caller,
        bytes memory _motionData,
        bytes memory _cancelData
    ) external;

    function execute(
        bytes memory _motionData,
        bytes memory _enactData
    ) external returns (bytes memory);
}
```

Executors are stored in an array and only the DAO can add or remove them:

```solidity=
address[] public executors;
mapping(address => uint256) private executorIndices;
```

To run an executor, `EasyTrackRegistry` calls executor's `execute` method and if it returns not empty slice of bytes will forward it as EVM script to Aragon Agent entity. On `EasyTrackRegistry` contract deployment, the Aragon Agent address is being saved in the contract and it cannot be updated later.

```solidity=
address public aragonAgent;
```

The contract also stores few parameters only owner can set:

- `uint256 public motionDuration` - Amount of time when owners of LDO can send an objection to reject the motion. This variable has a lower bound equal to 48 hours to exclude the possibility of attack with too low `motionDuration`. This value can be set only by DAO via regular Aragon voting. 
- `uint256 public objectionsThreshold` - Percent of governance tokens required to reject a proposal. The maximum limit for this value cannot be set at more than 5%. Default value is 0.5%. A value stored in basis points (500 equals 5%). This value can be set only by DAO via regular Aragon voting.
- `uint256 public motionsCountLimit` - Max number of active motions which can be stored in an easy tracks registry. This value is used to exclude opportunities to spam with easy tracks. It has an upper bound set by constant `MAX_MOTIONS_COUNT_LIMIT`(equals 128). Default limit value is 48 and can be set by DAO via regular Aragon voting.


### Modifiers


#### modifier onlyOwner()

Derives from the `OpenZeppelin/Ownable` contract. A method with this modifier can only be called by the contract owner.


#### modifier motionExists(uint256 _motionId)

Validates that the motion with given `_motionId` exists. Throws `"MOTION_NOT_FOUND"` otherwise.


### Methods


#### function setMotionDuration(uint256 _motionDuration) external onlyOwner

Sets the duration of newly created motions. Minimum value is 48 hours. The motion can only be enacted after this time in case the objections threshold has not been exceeded. Can only be called by the contract owner.

Events:
```solidity=
event MotionDurationChanged(uint256 _newDuration)
```


#### function setObjectionsThreshold(uint256 _objectionsThreshold) external onlyOwner

Sets new `objectionsThreshold` value. Maximum value is 5%. Can only be called by the contract owner.

Events:
```solidity=
event ObjectionsThresholdChanged(uint256 _newThreshold)
```

#### function setMotionsCountLimit(uint256 _motionsLimit) external onlyOwner

Sets new value for `motionsCountLimit`. Max value limitted by the `MAX_MOTIONS_COUNT_LIMIT` constant. Can only be called by the contract owner.

Events:
```solidity=
event MotionsCountLimitChanged(
    uint256 _newMotionsCountLimit
)
```


#### function sendObjection(uint256 _motionId) external motionExists(_motionId)

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


#### function getMotions() external view returns (Motion[] memory)

Returns list of motions not enacted and not canceled yet.


#### function getExecutors() external view returns (address[])

Returns array of active motion executors in the registry.


#### function addExecutor(address _executor) external onlyOwner

Adds a new `_executor` into the current list of executors. Can only be called by DAO upon Aragon voting.

Events:
```solidity=
event ExecutorAdded(address indexed _executor)
```

#### function deleteExecutor(address _executor) external onlyOwner

Removes executor with `_executor` address from the list of executors. If an executor was not found throws the `"EXECUTOR_NOT_FOUND"` error. Can only be called by DAO upon Aragon voting.

Events:
```solidity=
event ExecutorDeleted(address _executor)
```

#### function canSendObjection(uint256 _motionId, address _objector) external view motionExists(_motionId) returns (bool)

Returns if a user can submit an objection or not.


#### function createMotion(uint256 _executorId, bytes memory _data) external returns (uint256)

Method creates a new `Motion` and saves it into the respective mapping. This method also checks permissions by calling `beforeCreateMotionGuard` method on motion executor with given `_executorId` and `motionsCountLimit` value to limit amount of active motions. Returns id of created motion.

Method also has overloaded variant **`function createMotion(address _executor) external returns (uint256 _motionId)`** which passes empty bytes array as `_data` value.

Events:
```solidity=
event MotionCreated(
    uint256 indexed _motionId,
    uint256 indexed _executorId,
    bytes data
)
```

#### function cancelMotion(uint256 _motionId, bytes _cancelData) public

Method removes motion entity. `_data` contains additional parameters required in derived contracts (if required). This method also checks permissions by calling `beforeCancelMotionGuard` method on motion executor for a given `_motionId`.

Method also has overloaded variant **`function cancelMotion(uint256 _motionId) external`** which passes empty bytes array as `_cancelData` value.

Events:
```solidity=
event MotionCanceled(uint256 indexed _motionId)
```

#### function enactMotion(uint256 _motionId, bytes memory _enactData) public  motionExists(_motionId)

Method marks motion as enacted, calls executors `execute` method with passed params. If executor returns not empty aragon EVM script, will forward the script to the Aragon Agent. After that, method deletes the motion from the corresponding mapping. `EasyTrack` contract requires the role assigned to run EVM scripts on Agent entity.

Method also has overloaded variant **`function enactMotion(uint256 _motionId) external`** which passes empty bytes array as `_enactData` value.


Events:
```solidity=
event MotionEnacted(uint256 indexed _motionId)
```


## EasyTrackExecutor


`EasyTrackExecutor` is an abstract contract that can be used as the base class for new easy track executors. The contract has external methods `beforeCreateMotionGuard`, `beforeCancelMotionGuard` and `execute` used by `EasyTrackRegistry` in a lifecycle of motion. Above methods  check if the `msg.sender` matches the easy track registry contract address. 


### Storage Variables


To control access to contract's methods, the executor contract stores the address of the easy tracks registry contract:
```solidity=
address private easyTracksRegistry;
```
This variable is initially set in the contract constructor.


### Modifiers


####  modifier onlyEasyTrackRegistry
Validates that `msg.sender` equals `easyTracksRegistry` and throws `'NOT_EASY_TRACK_REGISTRY'` error otherwise.


### Methods


#### beforeCreateMotionGuard(address _caller, bytes memory _data) external override onlyEasyTrackRegistry

`EasyTracksRegistry` calls this method before the creation of a new motion, and the method only accepts calls from `EasyTracksRegistry`.
Method's implementation calls internal abstract method `_beforeCreateMotionGuard` which has to be overriden in derived contract and contain additional permissions checks if needed.


#### beforeCancelMotionGuard(address _caller, bytes memory _motionData, bytes memory _executionData) external override onlyEasyTrackRegistry

`EasyTracksRegistry` calls this method before the creation of a new motion, and the method only accepts calls from `EasyTracksRegistry`. 
Method's implementation calls internal abstract method `_beforeCancelMotionGuard` which has to be overriden in derived contract and contain additional permissions checks if needed.


#### function execute(bytes memory _motionData, bytes memory _executionData) external override onlyEasyTrackRegistry returns (bytes memory)

`EasyTracksRegistry` calls this method when enacts motion, and the method only accepts calls from `EasyTracksRegistry`. Method implementation calls internal abstract method `_execute` which has to be overriden in derived contract. If method returns not empty slice of bytes it will be passed to Aragon agent by the `EasyTracksRegistry` as EVM script.


#### function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal virtual

Method has no implementation and must be overridden in derived contract.

#### function _beforeCancelMotionGuard(address _caller, bytes memory _motionData, bytes memory _executionData) internal virtual

Method has no implementation and must be overridden in derived contract.

#### function _execute(bytes memory _motionData, bytes memory _enactData) internal virtual returns (bytes memory);

Method has no implementation and must be overridden in derived contract.


## TrustedAddress


Helper contract contains logic to validate that only a trusted address has access to certain methods. Might be inherited by other contracts to reduce amount of redundant code.


### Storage Variables

```solidity=
address private trustedAddress;
```


### Modifiers


#### modifier onlyTrustedAddress(address _caller)


Compares the passed `_caller` value to the current `trustedAddress` value and throws `"NOT_TRUSTED_ADDRESS"` in case addresses do not match.


## TopUpRewardProgramEasyTrackExecutor

Implements logic to transfer LDO into one or multiple allowed recipients. Inherits from `EasyTrackExecutor` and `TrustedAddress` contracts.

### Storage Variables
`rewardPrograms` array stores allowed reward transfer recipient addresses:

```solidity=
address[] public rewardPrograms;
mapping(address => uint256) private rewardProgramIndices;
```

Stores addresses of `AddRewardProgramEasyTrackExecutor` and `RemoveRewardProgramEasyTrackExecutor` contracts. Controlling list of allowed recipients might be done only by these addresses. Addresses set once after deploy in `initialize` method.

```solidity=
address public addRewardProgramEasyTrackExecutor;
address public removeRewardProgramEasyTrackExecutor;
```

### Methods

#### function initialize(address _addRewardProgramEasyTrackExecutor, address _removeRewardProgramEasyTrackExecutor) external
Sets values for `addRewardProgramEasyTrackExecutor` and `removeRewardProgramEasyTrackExecutor` variables if they haven't set yet. Throws `"ALREADY_INITIALIZED"` in other cases.

#### function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal view override onlyTrustedAddress(_caller)
`_data` bytes contains encoded value of type `(address[] _recipients, uint256[] _amounts)`. Checks if an each address in `_recipients` array contained in list of allowed reward programs.

#### function _beforeCancelMotionGuard(address _caller, bytes memory _motionData, bytes memory _cancelData) internal view override onlyTrustedAddress(_caller)

Checks if caller of the method is a trusted address.

#### function _execute(bytes memory _motionData, bytes memory _enactData) internal override returns (bytes memory)

Validates that every address from `_recipients` is whitelisted and returns EVM script to make transfers for corresponding amounts of LDO. If one or multiple addresses are not in the whitelist, it throws `"FORBIDDEN_ADDRESS"` error. 

#### function addRewardProgram(address _rewardProgram) external
Adds reward program address to `rewardPrograms` if it hasn't added yet, throws `"REWARD_PROGRAM_ALREADY_ADDED"` in other cases. Might be called only by `AddRewardProgramEasyTrackExecutor` contract.

#### function removeRewardProgram(address _rewardProgram) external
Removes reward program address from `rewardPrograms`. Throws `"REWARD_PROGRAM_NOT_FOUND"` if program address not in array. Might be called only by `RemoveRewardProgramEasyTrackExecutor` contract.


#### function isAllowed(address _rewardProgram) external view (returns bool)
Shows if address is whitelisted in `rewardPrograms`.


## AddRewardProgramEasyTrackExecutor
Implements logic to add new reward program from the list of allowed LDO recipients. Inherits from `EasyTrackExecutor` and `TrustedAddress` contracts.

### Storage Variables

Stores address of `TopUpRewardProgramEasyTrackExecutor`.

```solidity=
address public topUpRewardProgramEasyTrackExecutor;
```

### Methods

#### function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal view override onlyTrustedAddress(_caller)
`_data` bytes contains encoded value of type `(address _rewardProgram)`. Checks if an `_rewardProgram` hasn't whitelisted yet and throws `REWARD_PROGRAM_ALREADY_ADDED` in other case.

#### function _beforeCancelMotionGuard(address _caller, bytes memory _motionData, bytes memory _cancelData) internal view override onlyTrustedAddress(_caller)

Checks if caller of the method is a trusted address.

#### function _execute(bytes memory _motionData, bytes memory _enactData) internal override returns (bytes memory)
Calls `TopUpRewardProgramEasyTrackExecutor.addRewardProgram` method.


## RemoveRewardProgramEasyTrackExecutor
Implements logic to delete new reward program from the list of allowed LDO recipients. Inherits from EasyTrackExecutor and TrustedAddress contracts.

### Storage Variables
Stores address of `TopUpRewardProgramEasyTrackExecutor`.

```solidity=
address public topUpRewardProgramEasyTrackExecutor;
```

### Methods

#### function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal view override onlyTrustedAddress(_caller)
`_data` bytes contains encoded value of type `(address _rewardProgram)`. Checks if an `_rewardProgram` is in whitelist and throws `REWARD_PROGRAM_NOT_FOUND` in other case.

#### function _beforeCancelMotionGuard(address _caller, bytes memory _motionData, bytes memory _cancelData) internal view override onlyTrustedAddress(_caller)

Checks if caller of the method is a trusted address.

#### function _execute(bytes memory _motionData, bytes memory _enactData) internal override returns (bytes memory)
Calls `TopUpRewardProgramEasyTrackExecutor.removeRewardProgram` method.



## LegoEasyTrackExecutor

Implements logic to allocate LDO, stETH, or ETH for LEGO grants. This contract inherits from `EasyTrackExecutor` and `TrustedAddress` contracts.

### Storage Variables

Contract stores address of LEGO program:

```solidity=
address private legoProgram;
```


### Methods

#### function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal override onlyTrustedAddress(_caller)

Checks if a new motion can be created. `_data` bytes contains encoded value of type `(uint256 _ldoAmount, uint256 _stethAmount, uint256 _ethAmount)`. 
Runs the following checks:

- Requires at least one of `_ldoAmount`, `_stethAmount` or `_ethAmount` to be greater than zero.



#### function _beforeCancelMotionGuard(address _caller, bytes memory _motionData, bytes memory _cancelData) internal override onlyTrustedAddress(_caller)

Checks if the caller of the method is a trusted address.


#### function _execute(bytes memory _motionData, bytes memory _enactData) internal override returns (bytes memory)

Decodes motion `_data` to  value of type `(uint256 _ldoAmount, uint256 _stethAmount, uint256 _ethAmount)` and returns EVM script to transfer specified amount of tokens to `legoProgram`.


## NodeOperatorsEasyTrackExecutor

Implements logic to allow Lido NodeOperators create motions to increase their staking limits. This contract inherits from `EasyTrackExecutor` contract.


### Storage Variables

Contract stores address of `NodeOperatorsRegistry` contract:

```solidity=
NodeOperatorsRegistry public nodeOperatorsRegistry;
```

### Methods


#### function _beforeCreateMotionGuard(address _caller, bytes _data) internal override

Checks if a new motion can be created. `_data` bytes contains encoded value of type `(uint256 _nodeOperatorId, uint256 _stakingLimit)`. 
Runs checks as follows:

- Requires `NodeOperatorsRegistry` to contain node operator with given id.
- Requires the node operator to not be disabled.
- Requires the withdrawl address of the node operator to match the address of `_caller`.
- Requires the new value of `_stakingLimit` to be greater than the current value and less than or equal to the number of total signing keys of the node operator.


#### function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal override

Checks if the node operator id in the motion data exists in `NodeOperatorsRegistry` and if their withdrawal address matches the address of `_caller`. 


#### function _execute(bytes memory _motionData, bytes memory _enactData) internal override returns (bytes memory)

Creates EVM script which calls `NodeOperatorsRegistry.setNodeOperatorStakingLimit` method to update node operator staking limits. Before enacting, applies next sanity checks:

- Requires `NodeOperatorsRegistry` to contain node operator with given id.
- Requires the node operator to not be disabled
- Requires the new value of `_stakingLimit` to be greater than the current value and less than or equal to the number of total signing keys of the node operator.
