// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorRegestry.sol";
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
    /// @notice Address of Argon ACL contract
    IACL public immutable acl;

    // -------------
    // ERRORS
    // -------------

    string private constant MANAGER_ALREADY_HAS_ROLE = "MANAGER_ALREADY_HAS_ROLE";
    string private constant MANAGER_ADDRESSES_HAS_DUPLICATE = "MANAGER_ADDRESSES_HAS_DUPLICATE";
    string private constant NODE_OPERATORS_COUNT_MISMATCH = "NODE_OPERATORS_COUNT_MISMATCH";
    string private constant LIDO_REWARD_ADDRESS = "LIDO_REWARD_ADDRESS";
    string private constant ZERO_REWARD_ADDRESS = "ZERO_REWARD_ADDRESS";
    string private constant WRONG_NAME_LENGTH = "WRONG_NAME_LENGTH";
    string private constant MAX_OPERATORS_COUNT_EXCEEDED = "MAX_OPERATORS_COUNT_EXCEEDED";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _nodeOperatorsRegistry,
        address _acl
    ) TrustedCaller(_trustedCaller) {
        nodeOperatorsRegistry = INodeOperatorsRegistry(_nodeOperatorsRegistry);
        acl = IACL(_acl);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

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

        for (uint256 i = 0; i < decodedCallData.length; i++) {
            toAddresses[i * 2] = address(nodeOperatorsRegistry);
            methodIds[i * 2] = ADD_NODE_OPERATOR_SELECTOR;
            encodedCalldata[i * 2] = abi.encode(
                decodedCallData[i].name,
                decodedCallData[i].rewardAddress
            );

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
        address lido = nodeOperatorsRegistry.getLocator().lido();

        require(
            nodeOperatorsRegistry.getNodeOperatorsCount() == _nodeOperatorsCount,
            NODE_OPERATORS_COUNT_MISMATCH
        );

        require(
            _nodeOperatorsCount + _nodeOperatorInputs.length <=
                nodeOperatorsRegistry.MAX_NODE_OPERATORS_COUNT(),
            MAX_OPERATORS_COUNT_EXCEEDED
        );

        for (uint256 i = 0; i < _nodeOperatorInputs.length; i++) {
            for (uint256 testIndex = i + 1; testIndex < _nodeOperatorInputs.length; testIndex++) {
                require(
                    _nodeOperatorInputs[i].managerAddress !=
                        _nodeOperatorInputs[testIndex].managerAddress,
                    MANAGER_ADDRESSES_HAS_DUPLICATE
                );
            }

            require(
                acl.hasPermission(
                    _nodeOperatorInputs[i].managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == false,
                MANAGER_ALREADY_HAS_ROLE
            );
            require(
                acl.getPermissionParamsLength(
                    _nodeOperatorInputs[i].managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == 0,
                MANAGER_ALREADY_HAS_ROLE
            );

            require(_nodeOperatorInputs[i].rewardAddress != lido, LIDO_REWARD_ADDRESS);
            require(_nodeOperatorInputs[i].rewardAddress != address(0), ZERO_REWARD_ADDRESS);

            require(
                bytes(_nodeOperatorInputs[i].name).length > 0 &&
                    bytes(_nodeOperatorInputs[i].name).length <=
                    nodeOperatorsRegistry.MAX_NODE_OPERATOR_NAME_LENGTH(),
                WRONG_NAME_LENGTH
            );
        }
    }
}
