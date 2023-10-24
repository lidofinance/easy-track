// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./EVMScriptFactories/AddAllowedRecipient.sol";
import "./EVMScriptFactories/RemoveAllowedRecipient.sol";
import "./EVMScriptFactories/TopUpAllowedRecipients.sol";
import "./AllowedRecipientsRegistry.sol";
import "./AllowedTokensRegistry.sol";

/// @author bulbozaur
/// @notice Factory for Allowed Recipient Easy Track contracts
contract AllowedRecipientsFactory {
    event AllowedRecipientsRegistryDeployed(
        address indexed creator,
        address indexed allowedRecipientsRegistry,
        address _defaultAdmin,
        address[] addRecipientToAllowedListRoleHolders,
        address[] removeRecipientFromAllowedListRoleHolders,
        address[] setLimitParametersRoleHolders,
        address[] updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract bokkyPooBahsDateTimeContract
    );

    event AllowedTokensRegistryDeployed(
        address indexed creator,
        address indexed allowedTokensRegistry,
        address _defaultAdmin,
        address[] addTokenToAllowedListRoleHolders,
        address[] removeTokenFromAllowedListRoleHolders
    );

    event TopUpAllowedRecipientsDeployed(
        address indexed creator,
        address indexed topUpAllowedRecipients,
        address trustedCaller,
        address allowedRecipientsRegistry,
        address allowedTokenssRegistry,
        address finance,
        address easyTrack
    );

    event AddAllowedRecipientDeployed(
        address indexed creator,
        address indexed addAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    event RemoveAllowedRecipientDeployed(
        address indexed creator,
        address indexed removeAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    function deployAllowedRecipientsRegistry(
        address _defaultAdmin,
        address[] memory _addRecipientToAllowedListRoleHolders,
        address[] memory _removeRecipientFromAllowedListRoleHolders,
        address[] memory _setLimitParametersRoleHolders,
        address[] memory _updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    ) external returns (AllowedRecipientsRegistry registry) {
        registry = new AllowedRecipientsRegistry(
            _defaultAdmin,
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        );

        emit AllowedRecipientsRegistryDeployed(
            msg.sender,
            address(registry),
            _defaultAdmin,
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        );
    }

    function deployAllowedTokensRegistry(
        address _defaultAdmin,
        address[] memory _addTokensToAllowedListRoleHolders,
        address[] memory _removeTokensFromAllowedListRoleHolders
    ) external returns (AllowedTokensRegistry registry) {
        registry = new AllowedTokensRegistry(
            _defaultAdmin,
            _addTokensToAllowedListRoleHolders,
            _removeTokensFromAllowedListRoleHolders
        );

        emit AllowedTokensRegistryDeployed(
            msg.sender,
            address(registry),
            _defaultAdmin,
            _addTokensToAllowedListRoleHolders,
            _removeTokensFromAllowedListRoleHolders
        );
    }

    function deployTopUpAllowedRecipients(
        address _trustedCaller,
        address _allowedRecipientsRegistry,
        address _allowedTokensRegistry,
        address _finance,
        address _easyTrack
    ) external returns (TopUpAllowedRecipients topUpAllowedRecipients) {
        topUpAllowedRecipients = new TopUpAllowedRecipients(
            _trustedCaller,
            _allowedRecipientsRegistry,
            _allowedTokensRegistry,
            _finance,
            _easyTrack
        );

        emit TopUpAllowedRecipientsDeployed(
            msg.sender,
            address(topUpAllowedRecipients),
            _trustedCaller,
            _allowedRecipientsRegistry,
            _allowedTokensRegistry,
            _finance,
            _easyTrack
        );

        return topUpAllowedRecipients;
    }

    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry)
        external
        returns (AddAllowedRecipient addAllowedRecipient)
    {
        addAllowedRecipient = new AddAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        emit AddAllowedRecipientDeployed(
            msg.sender,
            address(addAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );
    }

    function deployRemoveAllowedRecipient(
        address _trustedCaller,
        address _allowedRecipientsRegistry
    ) external returns (RemoveAllowedRecipient removeAllowedRecipient) {
        removeAllowedRecipient = new RemoveAllowedRecipient(
            _trustedCaller,
            _allowedRecipientsRegistry
        );

        emit RemoveAllowedRecipientDeployed(
            msg.sender,
            address(removeAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );
    }
}
