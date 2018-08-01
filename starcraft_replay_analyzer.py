import os
import sys
import math

import sc2reader
from sc2reader.objects import Player
from sc2reader.resources import Replay

import techlabreactor

REPLAY_FOLDER_PATH = "C:\\Users\\ray\\Documents\\StarCraft II\\Accounts\\851727\\1-S2-1-328876\\Replays\\Multiplayer"

def main():

    path_to_replay_file = ""
    if len(sys.argv) < 2:
        path_to_replay_file = _get_path_to_most_recent_replay()
    else:
        path_to_replay_file = sys.argv[1]

    print("Path: ", path_to_replay_file)

    replay = sc2reader.load_replay(path_to_replay_file)

    print("\nAnalyzing replay: {}".format(replay.filename))

    analysis_cutoff_time_in_seconds = 600

    for player in replay.players:
        if player.play_race != "Zerg":
            continue

        print("\n{}".format(player))

        num_creep_tumors = techlabreactor.creep_tumours_built_before_second(analysis_cutoff_time_in_seconds, player, replay)
        print("\tNum creep tumors produced in first {} seconds: {}".format(analysis_cutoff_time_in_seconds, num_creep_tumors))

        avg_larvae_lifetime = average_larvae_lifetime(player, replay)
        print ("\tAverage larva lifetime: {}s".format(avg_larvae_lifetime))

        larvae_efficiency(player, replay)

        print_larvae_timeline(player, replay)

    return 0

def _get_path_to_most_recent_replay():
    replay_file_names = os.listdir(REPLAY_FOLDER_PATH)
    replay_file_full_paths = [os.path.join(REPLAY_FOLDER_PATH, replay_file_name) for replay_file_name in replay_file_names]

    most_recent_replay_filename = max(replay_file_full_paths, key=os.path.getctime)
    return most_recent_replay_filename

def larvae_efficiency(player: Player, replay: Replay) -> int:

    larvae_data = _get_larvae_data(player, replay)
    hatchery_data = _get_hatchery_data(player, replay)

    # Map larvae to their parent hatchery through the spawn location.
    for larvae in larvae_data.values():
        larvae_location = larvae["unit"].location

        closest_hatchery_id = ""
        closest_hatchery_distance = sys.maxsize
        for hatchery_id in hatchery_data:
            hatchery_spawn_location = hatchery_data[hatchery_id]["spawn_location"]

            distance_to_hatch = math.sqrt(
                (larvae_location[0] - hatchery_spawn_location[0])**2 + 
                (larvae_location[1] - hatchery_spawn_location[1])**2 )

            if distance_to_hatch < closest_hatchery_distance:
                closest_hatchery_id = hatchery_id
                closest_hatchery_distance = distance_to_hatch

        if "larvae" not in hatchery_data[closest_hatchery_id]:
            hatchery_data[closest_hatchery_id]["larvae"] = []

        hatchery_data[closest_hatchery_id]["larvae"].append(larvae)

    hatcheries = sorted(hatchery_data.values(), key=lambda hatchery: hatchery["started_at"] )

    hatch_number = 0
    for hatchery in hatcheries:
        hatch_number += 1

        hatchery_start_time = hatchery["started_at"]
        hatchery_end_time = hatchery["died_at"] if "died_at" in hatchery else _frame_to_second(replay.frames, replay)

        # We want ints so we can use an array where each bucket is a second,
        # so we can reconstruct our larvae timeline.
        hatchery_start_time = int(round(hatchery_start_time))
        hatchery_end_time = int(round(hatchery_end_time))
        hatch_lifetime = hatchery_end_time - hatchery_start_time

        larvae_timeline = [0] * hatch_lifetime

        for larva in hatchery["larvae"]:
            larva_start_time = int(round(larva["start_time"]))
            larva_start_time_in_timeline = larva_start_time - hatchery_start_time
            if larva_start_time_in_timeline < 0:
                larva_start_time_in_timeline = 0
            if larva_start_time_in_timeline >= hatch_lifetime:
                larva_start_time_in_timeline = hatch_lifetime - 1

            larvae_timeline[larva_start_time_in_timeline] += 1

            if "end_time" in larva:
                larva_end_time = int(round(larva["end_time"]))
                larva_end_time_in_timeline = larva_end_time - hatchery_start_time
                if larva_end_time_in_timeline < 0:
                    larva_end_time_in_timeline = 0
                if larva_end_time_in_timeline >= hatch_lifetime:
                    larva_end_time_in_timeline = hatch_lifetime - 1
                larvae_timeline[larva_end_time_in_timeline] -= 1

        larvae_total = 0
        num_timesteps_with_max_larvae = 0
        for timestep in larvae_timeline:
            larvae_total += timestep
            if larvae_total >= 3:
                num_timesteps_with_max_larvae += 1

        print("\n\tHatchery #{}:".format(hatch_number))
        print("\tCompleted at: {}s".format(hatchery_start_time))
        print("\tTotal larvae spawned: {}".format(len(hatchery["larvae"])))
        print("\tTime larvae capped: {:.1%}".format(num_timesteps_with_max_larvae / hatch_lifetime))
        print("\tNum larvae missed due to being capped: {}".format(int(num_timesteps_with_max_larvae / 11)))

    return 0

def print_larvae_timeline(player: Player, replay: Replay) -> int:

    larvae_data = _get_larvae_data(player, replay)

    MAX_TIMELINE_LENGTH = 900 # seconds
    timeline_end_time = min(MAX_TIMELINE_LENGTH, int(round(_frame_to_second(replay.frames, replay))))

    larvae_timeline = [0] * timeline_end_time

    for larva in larvae_data.values():
        larva_start_time = int(round(larva["start_time"]))
        if larva_start_time < 0:
            larva_start_time = 0
        if larva_start_time >= timeline_end_time:
            larva_start_time = timeline_end_time - 1
        larvae_timeline[larva_start_time] += 1

        if "end_time" in larva:
            larva_end_time = int(round(larva["end_time"]))
            if larva_end_time < 0:
                larva_end_time = 0
            if larva_end_time >= timeline_end_time:
                larva_end_time = timeline_end_time - 1
            larvae_timeline[larva_end_time] -= 1

    TIMESTEP_SIZE = 5 # seconds
    print("\nLarvae Timeline:")
    num_larvae = 0
    position_in_timeline = 0
    while position_in_timeline < len(larvae_timeline):
        num_larvae += larvae_timeline[position_in_timeline]

        if position_in_timeline % TIMESTEP_SIZE == 0:
            minutes, seconds = divmod(position_in_timeline, 60)
            timestamp_string = "%02d:%02d" % (minutes, seconds)
            larvae_graphic_string = "X" * num_larvae
            print("{}: {}".format(timestamp_string, larvae_graphic_string))

        position_in_timeline += 1


    return 0

def _get_hatchery_data(player: Player, replay: Replay) -> dict:
    hatcheries = set(
        event.unit for event
        in replay.tracker_events
        if (event.name in ["UnitDoneEvent", "UnitBornEvent"] and
            event.unit.owner == player and
            event.unit.name in ["Hatchery", "Lair", "Hive"])
    )

    # Seems like if you take a hatchery location and subtract 3 from its
    # y-coordinate you get prety close to where the larvae spawn, because they
    # spawn below the hatch.
    hatchery_spawn_location_y_offset = -3

    hatchery_data = {}
    for hatchery in hatcheries:
        spawn_location = ( hatchery.location[0], hatchery.location[1] + hatchery_spawn_location_y_offset )
        hatchery_data[hatchery.id] = { 
            "spawn_location": spawn_location,
            "started_at": _frame_to_second(hatchery.finished_at, replay) } # Use finished_at to avoid hatch build time

        if hatchery.died_at is not None:
            hatchery_data[hatchery.id]["died_at"] = _frame_to_second(hatchery.died_at, replay)

    return hatchery_data

def average_larvae_lifetime(player: Player, replay: Replay) -> int:
    
    larvae_data = _get_larvae_data(player, replay)

    lifetimes = []
    for larva in larvae_data.values():
        if "start_time" not in larva or "end_time" not in larva:
            continue

        lifetime = int(round(larva["end_time"] - larva["start_time"]))
        lifetimes.append(lifetime)

    return round(sum(lifetimes) / len(lifetimes), 1)

# TODO import properly from techlabreactor. For now copypasted here.
def _frame_to_second(frame: int, replay: Replay = None) -> float:
    fps = replay.game_fps if replay is not None else 16

    return frame / (1.4 * fps)

def _get_larvae_data(player: Player, replay: Replay) -> dict:

    larvae_data = {}

    larvae_units = set([
        event.unit
        for event
        in replay.events
        if (event.name in ["UnitBornEvent", "UnitDoneEvent"] and
            event.unit.owner == player and
            event.unit.name == "Larva" )
        ])
    for larva_unit in larvae_units:
        larvae_data[larva_unit.id] = {
            "unit": larva_unit, 
            "start_time": _frame_to_second(larva_unit.started_at, replay),
            "location": larva_unit.location
            }

    unit_type_change_events = [
        event for event in replay.events if event.name == "UnitTypeChangeEvent" and
        event.unit.owner == player and
        event.unit.name == "Larva"
        ]
    for unit_type_change_event in unit_type_change_events:
        unit_id = unit_type_change_event.unit.id
        end_time = int(round(_frame_to_second(unit_type_change_event.frame, replay)))

        if unit_id not in larvae_data:
            continue

        if ( "end_time" in larvae_data[unit_id] and
            end_time > larvae_data[unit_id]["end_time"]):
            continue

        larvae_data[unit_id]["end_time"] = end_time

    # num_have_end_time = len(list(filter(lambda x: "end_time" in x, larvae_data.values())))
    # num_total = len(larvae_data.values())
    # print("Num total: {}; Num have end time: {}".format(num_total, num_have_end_time))

    return larvae_data


# Attributes of an Event
# ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_str_prefix', 'frame', 'load_context', 'name', 'second', 'unit', 'unit_id', 'unit_id_index', 'unit_id_recycle', 'unit_type_name']

# attributes of a Unit
# ['__class__', '__cmp__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_type_class', 'apply_flags', 'died_at', 'finished_at', 'flags', 'hallucinated', 'id', 'is_army', 'is_building', 'is_type', 'is_worker', 'killed_by', 'killed_units', 'killing_player', 'killing_unit', 'location', 'minerals', 'name', 'owner', 'race', 'set_type', 'started_at', 'supply', 'title', 'type', 'type_history', 'vespene']

# Atributes of a Replay
#['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_get_datapack', '_get_reader', '_read_data', 'active_units', 'amm', 'archive', 'attributes', 'base_build', 'battle_net', 'build', 'category', 'client', 'clients', 'competitive', 'computer', 'computers', 'cooperative', 'datapack', 'date', 'end_time', 'entities', 'entity', 'events', 'expansion', 'factory', 'filehash', 'filename', 'frames', 'game_events', 'game_fps', 'game_length', 'game_type', 'hero_duplicates_allowed', 'human', 'humans', 'is_ladder', 'is_private', 'length', 'load_details', 'load_game_events', 'load_level', 'load_map', 'load_message_events', 'load_players', 'load_tracker_events', 'logger', 'map', 'map_file', 'map_hash', 'map_name', 'marked_error', 'message_events', 'messages', 'objects', 'observer', 'observers', 'opt', 'packets', 'people', 'people_hash', 'person', 'pings', 'player', 'players', 'plugin_failures', 'plugin_result', 'plugins', 'practice', 'ranked', 'raw_data', 'real_length', 'real_type', 'recorder', 'region', 'register_datapack', 'register_default_datapacks', 'register_default_readers', 'register_reader', 'registered_datapacks', 'registered_readers', 'release_string', 'resume_from_replay', 'resume_method', 'resume_user_info', 'speed', 'start_time', 'team', 'teams', 'time_zone', 'tracker_events', 'type', 'unit', 'units', 'unix_timestamp', 'versions', 'windows_timestamp', 'winner']

if __name__ == '__main__':
    main()