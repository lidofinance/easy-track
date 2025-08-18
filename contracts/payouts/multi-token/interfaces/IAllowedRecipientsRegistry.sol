// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

interface IAllowedRecipientsRegistry {
    function addRecipient(address _recipient, string memory _title) external;

    function renounceRole(bytes32 role, address account) external;

    function isRecipientAllowed(address _recipient) external view returns (bool);

    function setLimitParameters(uint256 _limit, uint256 _periodDurationMonths) external;

    function getLimitParameters() external view returns (uint256, uint256);

    function updateSpentAmount(uint256 _payoutAmount) external;

    function spendableBalance() external view returns (uint256);

    function hasRole(bytes32 role, address account) external view returns (bool);

    function getAllowedRecipients() external view returns (address[] memory);

    function bokkyPooBahsDateTimeContract() external view returns (address);

    function isUnderSpendableBalance(uint256 _amount, uint256 _motionDuration) external view returns (bool);
}