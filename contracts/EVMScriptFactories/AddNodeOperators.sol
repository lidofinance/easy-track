// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function addNodeOperator(
        string memory _name,
        address _rewardAddress
    ) external returns (uint256 id);

    function MAX_NODE_OPERATOR_NAME_LENGTH() external view returns (uint256);

    function MAX_NODE_OPERATORS_COUNT() external view returns (uint256);

    function getNodeOperatorsCount() external view returns (uint256);

    function getLocator() external view returns (ILidoLocator);
}

interface IACL {
    function grantPermissionP(
        address _entity,
        address _app,
        bytes32 _role,
        uint256[] memory _params
    ) external;

    function hasPermission(
        address _entity,
        address _app,
        bytes32 _role,
        uint256[] memory _params
    ) external view returns (bool);
}

interface ILidoLocator {
    function lido() external view returns (address);
}

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
    string private constant MANAGER_ADDRESSESS_HAS_DUPLICATE = "MANAGER_ADDRESSESS_HAS_DUPLICATE";
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

        for (uint i = 0; i < decodedCallData.length; i++) {
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
        uint256 nodeOperatorsCount,
        AddNodeOperatorInput[] memory nodeOperatorInputs
    ) private view {
        address lido = nodeOperatorsRegistry.getLocator().lido();

        require(
            nodeOperatorsRegistry.getNodeOperatorsCount() == nodeOperatorsCount,
            NODE_OPERATORS_COUNT_MISMATCH
        );

        require(
            nodeOperatorsCount + nodeOperatorInputs.length <=
                nodeOperatorsRegistry.MAX_NODE_OPERATORS_COUNT(),
            MAX_OPERATORS_COUNT_EXCEEDED
        );

        for (uint i = 0; i < nodeOperatorInputs.length; i++) {
            uint256[] memory permissionParams = new uint256[](1);
            permissionParams[0] = (1 << 240) + nodeOperatorsCount + i;
            for (uint test_index = i + 1; test_index < nodeOperatorInputs.length; test_index++) {
                require(
                    nodeOperatorInputs[i].managerAddress !=
                        nodeOperatorInputs[test_index].managerAddress,
                    MANAGER_ADDRESSESS_HAS_DUPLICATE
                );
            }
            require(
                acl.hasPermission(
                    nodeOperatorInputs[i].managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE,
                    permissionParams
                ) == false,
                MANAGER_ALREADY_HAS_ROLE
            );

            require(nodeOperatorInputs[i].rewardAddress != lido, LIDO_REWARD_ADDRESS);
            require(nodeOperatorInputs[i].rewardAddress != address(0), ZERO_REWARD_ADDRESS);

            require(
                bytes(nodeOperatorInputs[i].name).length > 0 &&
                    bytes(nodeOperatorInputs[i].name).length <=
                    nodeOperatorsRegistry.MAX_NODE_OPERATOR_NAME_LENGTH(),
                WRONG_NAME_LENGTH
            );
        }
    }
}
