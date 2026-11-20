// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

// -----------------------------------------------------------------------------
// The payouts contracts the integration scenarios deploy and drive: the registries, the
// top-up and recipient factories, and the builders that deploy them from the live Aragon
// apps. Interface names match the contracts under contracts/payouts and contracts/.
// -----------------------------------------------------------------------------

/// @notice `AllowedRecipientsRegistry`, a `LimitsChecker` over the recipient list. The events
///         are declared for `expectEmit`. Their layout matches the contract.
interface IAllowedRecipientsRegistry {
    event RecipientAdded(address indexed _recipient, string _title);

    event RecipientRemoved(address indexed _recipient);

    event SpendableAmountChanged(
        uint256 _alreadySpentAmount,
        uint256 _spendableBalance,
        uint256 indexed _periodStartTimestamp,
        uint256 _periodEndTimestamp
    );

    function ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE() external view returns (bytes32);

    function REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE() external view returns (bytes32);

    function hasRole(bytes32 role, address account) external view returns (bool);

    function grantRole(bytes32 role, address account) external;

    function addRecipient(address _recipient, string calldata _title) external;

    function removeRecipient(address _recipient) external;

    function isRecipientAllowed(address _recipient) external view returns (bool);

    function getAllowedRecipients() external view returns (address[] memory);

    function updateSpentAmount(uint256 _payoutAmount) external;

    function unsafeSetSpentAmount(uint256 _newSpentAmount) external;

    function isUnderSpendableBalance(uint256 _payoutAmount, uint256 _motionDuration)
        external
        view
        returns (bool);

    function spendableBalance() external view returns (uint256);

    function setLimitParameters(uint256 _limit, uint256 _periodDurationMonths) external;

    function getLimitParameters()
        external
        view
        returns (uint256 limit, uint256 periodDurationMonths);

    function getPeriodState()
        external
        view
        returns (
            uint256 _alreadySpentAmount,
            uint256 _spendableBalanceInPeriod,
            uint256 _periodStartTimestamp,
            uint256 _periodEndTimestamp
        );
}

/// @notice `AllowedTokensRegistry` of the multi-token payouts. `normalizeAmount` brings a token
///         amount to the 18 decimals the limits are kept in.
interface IAllowedTokensRegistry {
    function DEFAULT_ADMIN_ROLE() external view returns (bytes32);

    function ADD_TOKEN_TO_ALLOWED_LIST_ROLE() external view returns (bytes32);

    function REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE() external view returns (bytes32);

    function hasRole(bytes32 role, address account) external view returns (bool);

    function grantRole(bytes32 role, address account) external;

    function addToken(address _token) external;

    function removeToken(address _token) external;

    function isTokenAllowed(address _token) external view returns (bool);

    function normalizeAmount(uint256 _tokenAmount, address _token) external view returns (uint256);
}

/// @notice `TrustedCaller`, the base of the add, remove and top-up factories: the only account
///         allowed to create their motions.
interface ITrustedCaller {
    function trustedCaller() external view returns (address);
}

/// @notice `TopUpAllowedRecipients`, the multi-token top-up factory. Its calldata names the
///         token first.
interface ITopUpAllowedRecipients is ITrustedCaller {
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address token, address[] memory recipients, uint256[] memory amounts);
}

/// @notice `TopUpAllowedRecipientsSingleToken`, the top-up factory paying its one `token`.
interface ITopUpAllowedRecipientsSingleToken is ITrustedCaller {
    function token() external view returns (address);

    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory recipients, uint256[] memory amounts);
}

/// @notice `AllowedRecipientsFactory` of the multi-token payouts. Its builder's full setups return
///         nothing, so these events are the only record of the addresses they deployed. The
///         deployed contract is the second indexed argument of each.
interface IAllowedRecipientsFactory {
    event AllowedRecipientsRegistryDeployed(
        address indexed creator,
        address indexed allowedRecipientsRegistry,
        address _defaultAdmin,
        address[] addRecipientToAllowedListRoleHolders,
        address[] removeRecipientFromAllowedListRoleHolders,
        address[] setLimitParametersRoleHolders,
        address[] updateSpentAmountRoleHolders,
        address bokkyPooBahsDateTimeContract
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
}

/// @notice `AllowedRecipientsBuilder` of the multi-token payouts, over its factory, the Agent as
///         admin, Easy Track, Finance and the date-time contract.
interface IAllowedRecipientsBuilder {
    function factory() external view returns (address);

    function deployAllowedRecipientsRegistry(
        uint256 _limit,
        uint256 _periodDurationMonths,
        address[] calldata _recipients,
        string[] calldata _titles,
        uint256 _spentAmount,
        bool _grantRightsToEVMScriptExecutor
    ) external returns (IAllowedRecipientsRegistry);

    function deployAllowedTokensRegistry(address[] calldata _tokens)
        external
        returns (IAllowedTokensRegistry);

    function deployTopUpAllowedRecipients(
        address _trustedCaller,
        address _allowedRecipientsRegistry,
        address _allowedTokensRegistry
    ) external returns (ITopUpAllowedRecipients);

    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry)
        external
        returns (ITrustedCaller);

    function deployRemoveAllowedRecipient(
        address _trustedCaller,
        address _allowedRecipientsRegistry
    ) external returns (ITrustedCaller);

    function deployFullSetup(
        address _trustedCaller,
        uint256 _limit,
        uint256 _periodDurationMonths,
        address[] calldata _tokens,
        address[] calldata _recipients,
        string[] calldata _titles,
        uint256 _spentAmount
    ) external;

    function deploySingleRecipientTopUpOnlySetup(
        address _recipient,
        string calldata _title,
        address[] calldata _tokens,
        uint256 _limit,
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    ) external;
}

/// @notice `AllowedRecipientsBuilderSingleToken`, the same over the single-token factory.
interface IAllowedRecipientsBuilderSingleToken {
    function deployAllowedRecipientsRegistry(
        uint256 _limit,
        uint256 _periodDurationMonths,
        address[] calldata _recipients,
        string[] calldata _titles,
        uint256 _spentAmount,
        bool _grantRightsToEVMScriptExecutor
    ) external returns (IAllowedRecipientsRegistry);

    function deployTopUpAllowedRecipients(
        address _trustedCaller,
        address _allowedRecipientsRegistry,
        address _token
    ) external returns (ITopUpAllowedRecipientsSingleToken);

    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry)
        external
        returns (ITrustedCaller);

    function deployRemoveAllowedRecipient(
        address _trustedCaller,
        address _allowedRecipientsRegistry
    ) external returns (ITrustedCaller);

    function deployFullSetup(
        address _trustedCaller,
        address _token,
        uint256 _limit,
        uint256 _periodDurationMonths,
        address[] calldata _recipients,
        string[] calldata _titles,
        uint256 _spentAmount
    )
        external
        returns (
            IAllowedRecipientsRegistry allowedRecipientsRegistry,
            ITopUpAllowedRecipientsSingleToken topUpAllowedRecipients,
            ITrustedCaller addAllowedRecipient,
            ITrustedCaller removeAllowedRecipient
        );

    function deploySingleRecipientTopUpOnlySetup(
        address _recipient,
        string calldata _title,
        address _token,
        uint256 _limit,
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    )
        external
        returns (
            IAllowedRecipientsRegistry allowedRecipientsRegistry,
            ITopUpAllowedRecipientsSingleToken topUpAllowedRecipients
        );
}
