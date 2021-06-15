import random
import pytest

from brownie.network.state import Chain
from brownie import (
    EasyTracksRegistry,
    accounts,
    reverts,
    ZERO_ADDRESS,
)
from eth_abi import encode_single
from utils.evm_script import encode_call_script

import constants


def test_deploy(owner):
    "Must deploy EasyTracksRegistry contract with correct params"
    contract = owner.deploy(EasyTracksRegistry)
    assert contract.owner() == owner


def test_add_easy_track_called_by_owner(owner, easy_tracks_registry):
    "Must add new easy track with passed address to allowed"
    "easy tracks list and emit EasyTrackAdded event"
    easy_track = accounts[2]
    assert len(easy_tracks_registry.getEasyTracks()) == 0
    tx = easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == 1
    assert easy_tracks[0] == easy_track

    assert len(tx.events) == 1
    assert tx.events["EasyTrackAdded"]["_easyTrack"] == easy_track


def test_add_easy_track_called_by_stranger(
    stranger,
    easy_tracks_registry,
):
    "Must fail with error 'Ownable: caller is not the owner'"
    easy_track = accounts[2]
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.addEasyTrack(easy_track, {"from": stranger})


def test_add_easy_track_duplicate(owner, easy_tracks_registry):
    "Must fail with error 'EASY_TRACK_ALREADY_ADDED'"
    easy_track = accounts[2]
    assert len(easy_tracks_registry.getEasyTracks()) == 0
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == 1
    assert easy_tracks[0] == easy_track

    with reverts("EASY_TRACK_ALREADY_ADDED"):
        easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})


def test_delete_easy_track_called_by_owner(owner, easy_tracks_registry):
    "Must delete easy track from list of easy tracks and emits EasyTrackDeleted event"
    easy_track = accounts[2]
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    easyTracks = easy_tracks_registry.getEasyTracks()
    assert len(easyTracks) == 1
    assert easyTracks[0] == easy_track
    tx = easy_tracks_registry.deleteEasyTrack(easy_track)
    assert len(easy_tracks_registry.getEasyTracks()) == 0

    assert len(tx.events) == 1
    assert tx.events["EasyTrackDeleted"]["_easyTrack"] == easy_track


def test_delete_easy_track_not_exist(owner, easy_tracks_registry):
    "Must fail with error 'EASY_TRACK_NOT_FOUND'"
    easy_track = accounts[2]
    easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})
    assert len(easy_tracks_registry.getEasyTracks()) == 1
    with reverts("EASY_TRACK_NOT_FOUND"):
        easy_tracks_registry.deleteEasyTrack(accounts[1])


def test_delete_easy_track_with_empty_easy_tracks(owner, easy_tracks_registry):
    "Must fail with error 'EASY_TRACK_NOT_FOUND'"
    assert len(easy_tracks_registry.getEasyTracks()) == 0
    with reverts("EASY_TRACK_NOT_FOUND"):
        easy_tracks_registry.deleteEasyTrack(accounts[1])


def test_delete_easy_track_with_multiple_easy_tracks(
    owner,
    easy_tracks_registry,
):
    "Must remove exact easy tracks when listed many easy tracks"
    easy_tracks = accounts[2:7]

    # add easy tracks
    for easy_track in easy_tracks:
        easy_tracks_registry.addEasyTrack(easy_track, {"from": owner})

    listed_easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == len(listed_easy_tracks)

    while len(easy_tracks) > 0:
        index_to_delete = random.randint(0, len(easy_tracks) - 1)
        easy_track = easy_tracks.pop(index_to_delete)

        easy_tracks_registry.deleteEasyTrack(easy_track)
        listed_easy_tracks = easy_tracks_registry.getEasyTracks()

        assert len(easy_tracks) == len(listed_easy_tracks)

        # validate that was deleted correct address by join
        # test set with resulting set their size must be same
        assert len(set(easy_tracks).union(listed_easy_tracks)) == len(
            listed_easy_tracks
        )


def test_delete_motion_easy_track_called_by_stranger(stranger, easy_tracks_registry):
    "Must fail with error 'Ownable: caller is not the owner'"
    with reverts("Ownable: caller is not the owner"):
        easy_tracks_registry.deleteEasyTrack(ZERO_ADDRESS, {"from": stranger})
