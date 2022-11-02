// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./EVMScriptFactories/AddAllowedRecipient.sol";
import "./EVMScriptFactories/RemoveAllowedRecipient.sol";
import "./EVMScriptFactories/TopUpAllowedRecipients.sol";
import "./AllowedRecipientsRegistry.sol";

contract AllowedRecipientsFactory {

    bytes32 public constant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE");
    bytes32 public constant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE");
    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant SET_LIMIT_PARAMETERS_ROLE = keccak256("SET_LIMIT_PARAMETERS_ROLE");
    bytes32 public constant UPDATE_SPENT_AMOUNT_ROLE = keccak256("UPDATE_SPENT_AMOUNT_ROLE");

    string private constant ERROR_LENGTH_MISMATCH = "LENGTH_MISMATCH";

    address public immutable easyTrack;
    address public immutable finance;
    address public immutable evmScriptExecutor;
    address public immutable defaultAdmin;

    event AllowedRecipientsRegistryDeployed(
        address creator,
        address allowedRecipientsRegistry,
        address admin,
        IBokkyPooBahsDateTimeContract bokkyPooBahsDateTimeContract,
        uint256 limit, 
        uint256 periodDurationMonths,
        uint256 spentAmount
        // address[] addRecipientToAllowedListRoleHolders,
        // address[] removeRecipientFromAllowedListRoleHolders,
        // address[] setLimitParametersRoleHolders,
        // address[] updateSpentAmountRoleHolders,
        // address[] recipients, 
        // string[] titles
    );

    event FactoryInitialized(
        address easyTrack,
        address finance,
        address evmScriptExecutor,
        address defaultAdmin
    );

    event AddAllowedRecipientDeployed(
        address creator,
        address addAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    event RemoveAllowedRecipientDeployed(
        address creator,
        address removeAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    event TopUpAllowedRecipientsDeployed(
        address creator,
        address topUpAllowedRecipients,
        address trustedCaller,
        address allowedRecipientsRegistry,
        address finance,
        address token,
        address easyTrack
    );

    constructor(
        address _easytrack,
        address _finance,
        address _evmScriptExecutor,
        address _defaultAdmin
    ){
        easyTrack = _easytrack;
        finance = _finance;
        evmScriptExecutor = _evmScriptExecutor;
        defaultAdmin = _defaultAdmin;
        
        emit FactoryInitialized(_easytrack, _finance, _evmScriptExecutor, _defaultAdmin);
    }

    function deployAllowedRecipientsRegistry(
        address[] memory _recipients, 
        string[] memory _titles,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        uint256 _limit, 
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    ) public returns(AllowedRecipientsRegistry) 
    {
        require(_recipients.length == _titles.length, ERROR_LENGTH_MISMATCH);
        
        address[] memory addRecipientToAllowedListRoleHolders = new address[](3);
        addRecipientToAllowedListRoleHolders[0] = defaultAdmin;
        addRecipientToAllowedListRoleHolders[1] = evmScriptExecutor;
        addRecipientToAllowedListRoleHolders[2] = address(this);
        address[] memory removeRecipientFromAllowedListRoleHolders = new address[](2);
        removeRecipientFromAllowedListRoleHolders[0] = defaultAdmin;
        removeRecipientFromAllowedListRoleHolders[1] = evmScriptExecutor;
        address[] memory setLimitParametersRoleHolders = new address[](2);
        setLimitParametersRoleHolders[0] = defaultAdmin;
        setLimitParametersRoleHolders[1] = address(this);
        address[] memory updateSpentAmountRoleHolders = new address[](2);
        updateSpentAmountRoleHolders[0] = defaultAdmin;
        updateSpentAmountRoleHolders[1] = address(this);

        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            defaultAdmin, 
            addRecipientToAllowedListRoleHolders,
            removeRecipientFromAllowedListRoleHolders,
            setLimitParametersRoleHolders,
            updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        );
        
        for (uint256 i = 0; i < _recipients.length; i++) {
            registry.addRecipient(_recipients[i], _titles[i]);
        }
        registry.renounceRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this));

        require(registry.getAllowedRecipients().length == _recipients.length);

        for (uint256 i = 0; i < _recipients.length; i++) {
            registry.allowedRecipients(i) == _recipients[i];
        }       

        registry.setLimitParameters(_limit, _periodDurationMonths);
        registry.renounceRole(SET_LIMIT_PARAMETERS_ROLE, address(this));

        registry.updateSpentAmount(_spentAmount);
        registry.renounceRole(UPDATE_SPENT_AMOUNT_ROLE, address(this));

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, defaultAdmin));
        require(registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, defaultAdmin));
        require(registry.hasRole(DEFAULT_ADMIN_ROLE, defaultAdmin));

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evmScriptExecutor));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evmScriptExecutor));

        require(!registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, address(this)));
        require(!registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, address(this)));
        require(!registry.hasRole(DEFAULT_ADMIN_ROLE, address(this)));

        emit AllowedRecipientsRegistryDeployed(
            msg.sender,
            address(registry),
            defaultAdmin,
            _bokkyPooBahsDateTimeContract,
            _limit, 
            _periodDurationMonths,
            _spentAmount
        );

        // TODO: fix logging
            // addRecipientToAllowedListRoleHolders,
            // removeRecipientFromAllowedListRoleHolders,
            // setLimitParametersRoleHolders,
            // updateSpentAmountRoleHolders,
            // recipients, 
            // titles,

        return registry;
    }


    function deployTopUpAllowedRecipients(
        address _trustedCaller, 
        address _allowedRecipientsRegistry,
        address _token
    )   public returns(TopUpAllowedRecipients) 
    {      
        TopUpAllowedRecipients topUpAllowedRecipients = new TopUpAllowedRecipients(
            _trustedCaller,
            _allowedRecipientsRegistry,
            finance,
            _token,
            easyTrack
        );

        emit TopUpAllowedRecipientsDeployed(
            msg.sender,
            address(topUpAllowedRecipients),
            _trustedCaller,
            _allowedRecipientsRegistry,
            finance,
            _token,
            easyTrack
        );

        return topUpAllowedRecipients;
    }


    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry) 
        public
        returns(AddAllowedRecipient) 
    {
        AddAllowedRecipient addAllowedRecipient = 
            new AddAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        emit AddAllowedRecipientDeployed(
            msg.sender,
            address(addAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );

        return addAllowedRecipient;
    }

    
    function deployRemoveAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry) 
        public
        returns(RemoveAllowedRecipient) 
    {
        RemoveAllowedRecipient removeAllowedRecipient =
            new RemoveAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        emit RemoveAllowedRecipientDeployed(
            msg.sender,
            address(removeAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );

        return removeAllowedRecipient;
    }

    function deployFullSetup(
        address _trustedCaller,
        address _token, 
        address[] memory _recipients, 
        string[] memory _titles,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        uint256 _limit, 
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    ) public returns (address) {
        AllowedRecipientsRegistry registry = deployAllowedRecipientsRegistry(
            _recipients,
            _titles,
            _bokkyPooBahsDateTimeContract,
            _limit, 
            _periodDurationMonths,
            _spentAmount
        );

        TopUpAllowedRecipients topUpAllowedRecipients = deployTopUpAllowedRecipients(
            _trustedCaller, 
            address(registry),
            _token
        );

        AddAllowedRecipient addAllowedRecipient = deployAddAllowedRecipient(
            _trustedCaller, 
            address(registry)
        );

        RemoveAllowedRecipient removeAllowedRecipient = deployRemoveAllowedRecipient(
            _trustedCaller, 
            address(registry)
        );

    }

    function _deployTopUpOnlySetup(
        address _trustedCaller, 
        address _token, 
        address[] memory _recipients, 
        string[] memory _titles,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        uint256 _limit, 
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    ) public returns (address) {
        AllowedRecipientsRegistry registry = deployAllowedRecipientsRegistry(
            _recipients,
            _titles,
            _bokkyPooBahsDateTimeContract,
            _limit, 
            _periodDurationMonths,
            _spentAmount
        );

        TopUpAllowedRecipients topUpAllowedRecipients = deployTopUpAllowedRecipients(
            _trustedCaller, 
            address(registry),
            _token
        );
    }
}
