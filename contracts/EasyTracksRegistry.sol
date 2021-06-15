// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/access/Ownable.sol";

contract EasyTracksRegistry is Ownable {
    event EasyTrackAdded(address indexed _easyTrack);
    event EasyTrackDeleted(address indexed _easyTrack);

    string private constant ERROR_EASY_TRACK_ALREADY_ADDED = "EASY_TRACK_ALREADY_ADDED";
    string private constant ERROR_EASY_TRACK_NOT_FOUND = "EASY_TRACK_NOT_FOUND";

    address[] public easyTracks;
    mapping(address => uint256) private easyTrackIndices;

    /**
     @notice Adds a new `_easyTrack` into the current list of easyTracks.
     Can be callend only by owner of contract.
     */
    function addEasyTrack(address _easyTrack) external onlyOwner {
        require(easyTrackIndices[_easyTrack] == 0, ERROR_EASY_TRACK_ALREADY_ADDED);
        easyTracks.push(_easyTrack);
        easyTrackIndices[_easyTrack] = easyTracks.length;
        emit EasyTrackAdded(_easyTrack);
    }

    function deleteEasyTrack(address _easyTrack) external onlyOwner {
        uint256 index = _getEasyTrackIndex(_easyTrack);
        uint256 lastIndex = easyTracks.length - 1;

        if (index != lastIndex) {
            address lastEasyTrack = easyTracks[lastIndex];
            easyTracks[index] = lastEasyTrack;
            easyTrackIndices[lastEasyTrack] = index + 1;
        }

        easyTracks.pop();
        delete easyTrackIndices[_easyTrack];
        emit EasyTrackDeleted(_easyTrack);
    }

    function isEasyTrack(address _maybeEasyTrack) external view returns (bool) {
        return easyTrackIndices[_maybeEasyTrack] > 0;
    }

    /**
     @notice Returns list of active easyTracks
     */
    function getEasyTracks() external view returns (address[] memory result) {
        return easyTracks;
    }

    function _getEasyTrackIndex(address _easyTrack) private view returns (uint256 _index) {
        _index = easyTrackIndices[_easyTrack];
        require(_index > 0, ERROR_EASY_TRACK_NOT_FOUND);
        _index -= 1;
    }

    modifier easyTrackExists(address _easyTrack) {
        require(easyTrackIndices[_easyTrack] > 0, ERROR_EASY_TRACK_NOT_FOUND);
        _;
    }
}
