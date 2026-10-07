// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IEVMScriptExecutor} from "test/foundry/interfaces/EasyTrack.sol";
import {IACL, INodeOperatorsRegistry} from "test/foundry/interfaces/External.sol";
import {IAddNodeOperators, INodeOperatorsFactory} from "test/foundry/interfaces/Factories.sol";

/// @notice Harness for the SimpleDVT scenarios: the deployed node operator factories of
///         `deployed-<chain>.json` drive the SimpleDVT registry they target. A scenario adds its
///         operators on top of the registry's current ones and addresses them by index, see
///         `_operatorId`. Each gets the low address of `_operatorAddress` as reward address and
///         manager, as the Brownie suite assigns them.
abstract contract SimpleDvtScenarioBase is EasyTrackScenarioBase {
    /// @dev `AddNodeOperators.AddNodeOperatorInput`
    struct AddNodeOperatorInput {
        string name;
        address rewardAddress;
        address managerAddress;
    }

    /// @dev `ActivateNodeOperators.ActivateNodeOperatorInput` and
    ///      `DeactivateNodeOperators.DeactivateNodeOperatorInput`, one layout
    struct OperatorManagerInput {
        uint256 nodeOperatorId;
        address managerAddress;
    }

    /// @dev `ChangeNodeOperatorManagers.ChangeNodeOperatorManagersInput`
    struct ChangeNodeOperatorManagersInput {
        uint256 nodeOperatorId;
        address oldManagerAddress;
        address newManagerAddress;
    }

    /// @dev `SetNodeOperatorNames.SetNameInput`
    struct SetNameInput {
        uint256 nodeOperatorId;
        string name;
    }

    /// @dev `SetNodeOperatorRewardAddresses.SetRewardAddressInput`
    struct SetRewardAddressInput {
        uint256 nodeOperatorId;
        address rewardAddress;
    }

    /// @dev `SetVettedValidatorsLimits.VettedValidatorsLimitInput`, an entry of its array, and the
    ///      single tuple `IncreaseVettedValidatorsLimit` takes
    struct VettedValidatorsLimitInput {
        uint256 nodeOperatorId;
        uint256 stakingLimit;
    }

    /// @dev `UpdateTargetValidatorLimits.TargetValidatorsLimit`
    struct TargetValidatorsLimit {
        uint256 nodeOperatorId;
        uint256 targetLimitMode;
        uint256 targetLimit;
    }

    bytes32 internal constant MANAGE_SIGNING_KEYS = keccak256("MANAGE_SIGNING_KEYS");

    /// @dev Aragon CallsScript spec id, the prefix of every EVM script
    bytes4 private constant SPEC_ID = 0x00000001;

    /// @dev Three deposit keys with their signatures, added to an operator in one call
    uint256 internal constant SIGNING_KEYS_COUNT = 3;
    bytes internal constant SIGNING_KEYS_PUBKEYS = hex"8bb1db218877a42047b953bdc32573445a78d93383ef5fd08f79c066d4781961db4f5ab5a7cc0cf1e4cbcc23fd17f9d7"
        hex"884b147305bcd9fce3a1cc12e8f893c6356c1780688286277656e1ba724a3fde49262c98503141c0925b344a8ccea9ca"
        hex"952ff22cf4a5f9708d536acb2170f83c137301515df5829adc28c265373487937cc45e8f91743caba0b9ebd02b3b664f";
    bytes internal constant SIGNING_KEYS_SIGNATURES = hex"ad17ef7cdf0c4917aaebc067a785b049d417dda5d4dd66395b21bbd50781d51e28ee750183eca3d32e1f57b324049a06135ad07d1aa243368bca9974e25233f050e0d6454894739f87faace698b90ea65ee4baba2758772e09fec4f1d8d35660"
        hex"9794e7871dc766c2139f9476234bc29784e13b51e859445044d2a5a9df8bc072d9c51c51ee69490ce37bdfc7cf899af2166b0710d620a87398d5ec7da06c9f7eb27f1d729973efd60052dbd4cb7f43ff6b141af4d0a0a980b60f663f39bf7844"
        hex"90111fb6944ff8b56eb0858c1deb91f41c8c631573f4c821663d7079e5e78903d67fa1c4a4ed358378f16a2b7ec524c5196b1a1eae35b01dca1df74535f45d6bd1960164a41425b2a289d4bb5c837049acf5871a0ed23598df42f6234276f6e2";

    INodeOperatorsRegistry internal simpleDvt;
    IACL internal acl;

    address internal addNodeOperators;
    address internal activateNodeOperators;
    address internal deactivateNodeOperators;
    address internal setNodeOperatorNames;
    address internal setNodeOperatorRewardAddresses;
    address internal setVettedValidatorsLimits;
    address internal increaseVettedValidatorsLimit;
    address internal updateTargetValidatorLimits;
    address internal changeNodeOperatorManagers;

    /// @dev The id the scenario's first operator gets, the registry's count before the scenario
    uint256 internal firstOperatorId;

    function setUp() public virtual {
        _forkAndInitialize();

        IAddNodeOperators factory =
            IAddNodeOperators(_factoryAddress(config.artifact, "AddNodeOperators"));
        simpleDvt = INodeOperatorsRegistry(factory.nodeOperatorsRegistry());
        acl = IACL(factory.acl());
        firstOperatorId = simpleDvt.getNodeOperatorsCount();

        vm.label(address(factory), "AddNodeOperators");
        vm.label(address(simpleDvt), "SimpleDVT");
        vm.label(address(acl), "ACL");

        // The committee trusted by `AddNodeOperators` creates every trusted factory's motions
        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
        addNodeOperators = address(factory);
        activateNodeOperators = _trustedFactory("ActivateNodeOperators");
        deactivateNodeOperators = _trustedFactory("DeactivateNodeOperators");
        setNodeOperatorNames = _trustedFactory("SetNodeOperatorNames");
        setNodeOperatorRewardAddresses = _trustedFactory("SetNodeOperatorRewardAddresses");
        setVettedValidatorsLimits = _trustedFactory("SetVettedValidatorsLimits");
        increaseVettedValidatorsLimit = _factory("IncreaseVettedValidatorsLimit");
        updateTargetValidatorLimits = _trustedFactory("UpdateTargetValidatorLimits");
        changeNodeOperatorManagers = _trustedFactory("ChangeNodeOperatorManagers");
    }

    // --- operators ---

    /// @dev The id of the scenario's operator at `index`
    function _operatorId(uint256 index) internal view returns (uint256) {
        return firstOperatorId + index;
    }

    /// @dev The reward address and manager of the scenario's operator at `index`
    function _operatorAddress(uint256 index) internal pure returns (address) {
        return address(uint160(index + 1));
    }

    function _clusterName(uint256 index) internal pure returns (string memory) {
        return string.concat("Cluster ", vm.toString(index + 1));
    }

    /// @dev Whether `manager` holds `MANAGE_SIGNING_KEYS` for the operator, the parameterized ACL
    ///      grant the add and change-manager factories make
    function _canManageSigningKeys(address manager, uint256 nodeOperatorId)
        internal
        view
        returns (bool)
    {
        uint256[] memory params = new uint256[](1);
        params[0] = nodeOperatorId;

        return simpleDvt.canPerform(manager, MANAGE_SIGNING_KEYS, params);
    }

    /// @dev The operator's manager adds the three signing keys directly, outside Easy Track
    function _addSigningKeys(uint256 nodeOperatorId, address manager) internal {
        vm.prank(manager);
        simpleDvt.addSigningKeysOperatorBH(
            nodeOperatorId, SIGNING_KEYS_COUNT, SIGNING_KEYS_PUBKEYS, SIGNING_KEYS_SIGNATURES
        );
    }

    /// @dev `count` clusters named by index, each its own reward address and manager
    function _encodeAddClusters(uint256 count) internal view returns (bytes memory) {
        AddNodeOperatorInput[] memory inputs = new AddNodeOperatorInput[](count);
        for (uint256 index; index < count; ++index) {
            inputs[index] = AddNodeOperatorInput({
                name: _clusterName(index),
                rewardAddress: _operatorAddress(index),
                managerAddress: _operatorAddress(index)
            });
        }

        return abi.encode(firstOperatorId, inputs);
    }

    /// @dev The cluster at `index` is active, named and addressed as added, has no keys, and its
    ///      manager may manage its signing keys
    function _assertClusterAdded(uint256 index) internal view {
        string memory cluster = _clusterName(index);
        (
            bool active,
            string memory name,
            address rewardAddress,
            uint64 totalVettedValidators,
            uint64 totalExitedValidators,
            uint64 totalAddedValidators,
            uint64 totalDepositedValidators
        ) = simpleDvt.getNodeOperator(_operatorId(index), true);

        assertTrue(active, string.concat(cluster, " active"));
        assertEq(name, cluster, string.concat(cluster, " name"));
        assertEq(rewardAddress, _operatorAddress(index), string.concat(cluster, " rewardAddress"));
        assertEq(totalVettedValidators, 0, string.concat(cluster, " totalVettedValidators"));
        assertEq(totalExitedValidators, 0, string.concat(cluster, " totalExitedValidators"));
        assertEq(totalAddedValidators, 0, string.concat(cluster, " totalAddedValidators"));
        assertEq(totalDepositedValidators, 0, string.concat(cluster, " totalDepositedValidators"));
        assertTrue(
            _canManageSigningKeys(_operatorAddress(index), _operatorId(index)),
            string.concat(cluster, " canPerform")
        );
    }

    // --- DAO vote ---

    /// @dev Replay a DAO vote acting through the executor: Voting points the executor at the
    ///      Agent, the Agent runs the single-call script, Voting points it back at Easy Track
    function _executeDaoScript(address target, bytes memory callData) internal {
        IEVMScriptExecutor executor = IEVMScriptExecutor(evmScriptExecutor);
        address voting = _voting();

        vm.prank(voting);
        executor.setEasyTrack(config.agent);

        vm.prank(config.agent);
        executor.executeEVMScript(_encodeCallScript(target, callData));

        vm.prank(voting);
        executor.setEasyTrack(address(easyTrack));
    }

    /// @dev An Aragon CallsScript of one call: `[spec id][target][calldata length][calldata]`
    function _encodeCallScript(address target, bytes memory callData)
        private
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(SPEC_ID, target, uint32(callData.length), callData);
    }

    // --- calldata ---

    /// @dev `(uint256 nodeOperatorsCount, AddNodeOperatorInput[])` of one operator
    function _encodeAddNodeOperator(
        uint256 nodeOperatorsCount,
        string memory name,
        address rewardAddress,
        address managerAddress
    ) internal pure returns (bytes memory) {
        AddNodeOperatorInput[] memory inputs = new AddNodeOperatorInput[](1);
        inputs[0] = AddNodeOperatorInput(name, rewardAddress, managerAddress);

        return abi.encode(nodeOperatorsCount, inputs);
    }

    /// @dev `(ActivateNodeOperatorInput[])` or `(DeactivateNodeOperatorInput[])` of one operator
    function _encodeOperatorManager(uint256 nodeOperatorId, address managerAddress)
        internal
        pure
        returns (bytes memory)
    {
        OperatorManagerInput[] memory inputs = new OperatorManagerInput[](1);
        inputs[0] = OperatorManagerInput(nodeOperatorId, managerAddress);

        return abi.encode(inputs);
    }

    /// @dev `(ChangeNodeOperatorManagersInput[])` of one operator
    function _encodeChangeManager(
        uint256 nodeOperatorId,
        address oldManagerAddress,
        address newManagerAddress
    ) internal pure returns (bytes memory) {
        ChangeNodeOperatorManagersInput[] memory inputs = new ChangeNodeOperatorManagersInput[](1);
        inputs[0] =
            ChangeNodeOperatorManagersInput(nodeOperatorId, oldManagerAddress, newManagerAddress);

        return abi.encode(inputs);
    }

    /// @dev `(SetNameInput[])` of one operator
    function _encodeSetName(uint256 nodeOperatorId, string memory name)
        internal
        pure
        returns (bytes memory)
    {
        SetNameInput[] memory inputs = new SetNameInput[](1);
        inputs[0] = SetNameInput(nodeOperatorId, name);

        return abi.encode(inputs);
    }

    /// @dev `(SetRewardAddressInput[])` of one operator
    function _encodeSetRewardAddress(uint256 nodeOperatorId, address rewardAddress)
        internal
        pure
        returns (bytes memory)
    {
        SetRewardAddressInput[] memory inputs = new SetRewardAddressInput[](1);
        inputs[0] = SetRewardAddressInput(nodeOperatorId, rewardAddress);

        return abi.encode(inputs);
    }

    /// @dev `(VettedValidatorsLimitInput[])` of one operator
    function _encodeSetVettedLimit(uint256 nodeOperatorId, uint256 stakingLimit)
        internal
        pure
        returns (bytes memory)
    {
        VettedValidatorsLimitInput[] memory inputs = new VettedValidatorsLimitInput[](1);
        inputs[0] = VettedValidatorsLimitInput(nodeOperatorId, stakingLimit);

        return abi.encode(inputs);
    }

    /// @dev The single `VettedValidatorsLimitInput` tuple `IncreaseVettedValidatorsLimit` takes,
    ///      not an array
    function _encodeIncreaseVettedLimit(uint256 nodeOperatorId, uint256 stakingLimit)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encode(VettedValidatorsLimitInput(nodeOperatorId, stakingLimit));
    }

    // --- factories ---

    /// @dev A deployed factory targeting the registry and trusting the same committee as
    ///      `AddNodeOperators`
    function _trustedFactory(string memory key) private returns (address factory) {
        factory = _factory(key);

        assertEq(
            INodeOperatorsFactory(factory).trustedCaller(),
            creator,
            string.concat("setup: ", key, " trustedCaller")
        );
    }

    /// @dev A deployed factory targeting the registry
    function _factory(string memory key) private returns (address factory) {
        factory = _factoryAddress(config.artifact, key);
        vm.label(factory, key);

        assertEq(
            INodeOperatorsFactory(factory).nodeOperatorsRegistry(),
            address(simpleDvt),
            string.concat("setup: ", key, " nodeOperatorsRegistry")
        );
    }
}
