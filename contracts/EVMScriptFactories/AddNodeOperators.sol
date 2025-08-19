// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IACL.sol";

/// @notice Creates EVMScript to add new batch of node operators
contract AddNodeOperators is TrustedCaller, IEVMScriptFactory {
    struct AddNodeOperatorInput {
        string name;
        address rewardAddress;
        address managerAddress;
    }

    // -------------
    // CONSTANTS
    // -------------

    bytes4 private constant ADD_NODE_OPERATOR_SELECTOR =
        bytes4(keccak256("addNodeOperator(string,address)"));
    bytes4 private constant GRANT_PERMISSION_P_SELECTOR =
        bytes4(keccak256("grantPermissionP(address,address,bytes32,uint256[])"));
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;
    /// @notice Address of Aragon ACL contract
    IACL public immutable acl;
    /// @notice Address of Lido contract
    address public immutable lido;

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_MANAGER_ALREADY_HAS_ROLE = "MANAGER_ALREADY_HAS_ROLE";
    string private constant ERROR_MANAGER_ADDRESSES_HAS_DUPLICATE =
        "MANAGER_ADDRESSES_HAS_DUPLICATE";
    string private constant ERROR_NODE_OPERATORS_COUNT_MISMATCH = "NODE_OPERATORS_COUNT_MISMATCH";
    string private constant ERROR_LIDO_REWARD_ADDRESS = "LIDO_REWARD_ADDRESS";
    string private constant ERROR_ZERO_REWARD_ADDRESS = "ZERO_REWARD_ADDRESS";
    string private constant ERROR_ZERO_MANAGER_ADDRESS = "ZERO_MANAGER_ADDRESS";
    string private constant ERROR_WRONG_NAME_LENGTH = "WRONG_NAME_LENGTH";
    string private constant ERROR_MAX_OPERATORS_COUNT_EXCEEDED = "MAX_OPERATORS_COUNT_EXCEEDED";
    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _nodeOperatorsRegistry,
        address _acl,
        address _lido
    ) TrustedCaller(_trustedCaller) {
        nodeOperatorsRegistry = INodeOperatorsRegistry(_nodeOperatorsRegistry);
        acl = IACL(_acl);
        lido = _lido;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to add batch of node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (uint256,AddNodeOperatorInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        (
            uint256 nodeOperatorsCount,
            AddNodeOperatorInput[] memory decodedCallData
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        address[] memory toAddresses = new address[](decodedCallData.length * 2);
        bytes4[] memory methodIds = new bytes4[](decodedCallData.length * 2);
        bytes[] memory encodedCalldata = new bytes[](decodedCallData.length * 2);

        _validateInputData(nodeOperatorsCount, decodedCallData);

        for (uint256 i = 0; i < decodedCallData.length; ++i) {
            toAddresses[i * 2] = address(nodeOperatorsRegistry);
            methodIds[i * 2] = ADD_NODE_OPERATOR_SELECTOR;
            encodedCalldata[i * 2] = abi.encode(
                decodedCallData[i].name,
                decodedCallData[i].rewardAddress
            );

            // See https://legacy-docs.aragon.org/developers/tools/aragonos/reference-aragonos-3#parameter-interpretation for details
            uint256[] memory permissionParams = new uint256[](1);
            permissionParams[0] = (1 << 240) + nodeOperatorsCount + i;

            toAddresses[i * 2 + 1] = address(acl);
            methodIds[i * 2 + 1] = GRANT_PERMISSION_P_SELECTOR;
            encodedCalldata[i * 2 + 1] = abi.encode(
                decodedCallData[i].managerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE,
                permissionParams
            );
        }

        return EVMScriptCreator.createEVMScript(toAddresses, methodIds, encodedCalldata);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (uint256, AddNodeOperatorInput[])
    /// @return nodeOperatorsCount current number of node operators in registry
    /// @return nodeOperators AddNodeOperatorInput[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    )
        external
        pure
        returns (uint256 nodeOperatorsCount, AddNodeOperatorInput[] memory nodeOperators)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    )
        private
        pure
        returns (uint256 nodeOperatorsCount, AddNodeOperatorInput[] memory nodeOperators)
    {
        (nodeOperatorsCount, nodeOperators) = abi.decode(
            _evmScriptCallData,
            (uint256, AddNodeOperatorInput[])
        );
    }

    function _validateInputData(
        uint256 _nodeOperatorsCount,
        AddNodeOperatorInput[] memory _nodeOperatorInputs
    ) private view {
        uint256 maxNameLength = nodeOperatorsRegistry.MAX_NODE_OPERATOR_NAME_LENGTH();
        uint256 calldataLength = _nodeOperatorInputs.length;

        require(calldataLength > 0, ERROR_EMPTY_CALLDATA);
        
        require(
            nodeOperatorsRegistry.getNodeOperatorsCount() == _nodeOperatorsCount,
            ERROR_NODE_OPERATORS_COUNT_MISMATCH
        );

        require(
            _nodeOperatorsCount + calldataLength <= nodeOperatorsRegistry.MAX_NODE_OPERATORS_COUNT(),
            ERROR_MAX_OPERATORS_COUNT_EXCEEDED
        );

        for (uint256 i = 0; i < calldataLength; ++i) {
            address managerAddress = _nodeOperatorInputs[i].managerAddress;
            address rewardAddress = _nodeOperatorInputs[i].rewardAddress;
            string memory name = _nodeOperatorInputs[i].name;
            for (uint256 testIndex = i + 1; testIndex < calldataLength; ++testIndex) {
                require(
                    managerAddress != _nodeOperatorInputs[testIndex].managerAddress,
                    ERROR_MANAGER_ADDRESSES_HAS_DUPLICATE
                );
            }

            require(
                acl.hasPermission(
                    managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == false,
                ERROR_MANAGER_ALREADY_HAS_ROLE
            );
            require(
                acl.getPermissionParamsLength(
                    managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == 0,
                ERROR_MANAGER_ALREADY_HAS_ROLE
            );

            require(rewardAddress != lido, ERROR_LIDO_REWARD_ADDRESS);
            require(rewardAddress != address(0), ERROR_ZERO_REWARD_ADDRESS);
            require(managerAddress != address(0), ERROR_ZERO_MANAGER_ADDRESS);

            require(
                bytes(name).length > 0 && bytes(name).length <= maxNameLength,
                ERROR_WRONG_NAME_LENGTH
            );
        }
    }
}
