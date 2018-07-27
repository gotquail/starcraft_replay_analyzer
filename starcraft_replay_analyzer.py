import sys

import sc2reader
from sc2reader.objects import Player
from sc2reader.resources import Replay

import techlabreactor

def main():
    path = sys.argv[1]
    replay = sc2reader.load_replay(path)

    print(replay.filename)

    # Num creep tumors in first 10 mins.
    num_creep_tumors = techlabreactor.creep_tumours_built_before_second(600, replay.players[0], replay)
    print("Num creep tumors produced in first 10 minutes: ", num_creep_tumors)

    # Num larvae
    num_larvae = num_larvae_produced_before_second(600, replay.players[0], replay)
    print("Num larvae produced in first 10 minutes: ", num_larvae)

    avg_larvae_lifetime = average_larvae_lifetime(replay.players[0], replay)
    print ("Average larva lifetime: ", avg_larvae_lifetime, "s")

    return 0

def _frame_to_second(frame: int, replay: Replay = None) -> float:
    fps = replay.game_fps if replay is not None else 16

    return frame / (1.4 * fps)

def larvae_efficiency(player: Player, replay: Replay) -> int:

    return 0

def average_larvae_lifetime(player: Player, replay: Replay) -> int:
    
    larvae_data = _get_larvae_data(player, replay)

    lifetimes = []
    for larva in larvae_data.values():
        if "start_time" not in larva or "end_time" not in larva:
            continue

        lifetime = int(round(larva["end_time"] - larva["start_time"]))
        lifetimes.append(lifetime)

    return round(sum(lifetimes) / len(lifetimes), 1)

def _get_larvae_data(player: Player, replay: Replay) -> dict:

    larvae_data = {}

    larvae_units = set([
        event.unit
        for event
        in replay.events
        if (event.name in ["UnitBornEvent"] and
            event.unit.owner == player and
            event.unit.name == "Larva" )
        ])
    for larva_unit in larvae_units:
        larvae_data[larva_unit.id] = {
            "unit": larva_unit, 
            "start_time": _frame_to_second(larva_unit.started_at, replay)
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

    return larvae_data



# Attributes of an Event
# ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_str_prefix', 'frame', 'load_context', 'name', 'second', 'unit', 'unit_id', 'unit_id_index', 'unit_id_recycle', 'unit_type_name']

# attributes of a Unit
# ['__class__', '__cmp__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_type_class', 'apply_flags', 'died_at', 'finished_at', 'flags', 'hallucinated', 'id', 'is_army', 'is_building', 'is_type', 'is_worker', 'killed_by', 'killed_units', 'killing_player', 'killing_unit', 'location', 'minerals', 'name', 'owner', 'race', 'set_type', 'started_at', 'supply', 'title', 'type', 'type_history', 'vespene']

def num_larvae_produced_before_second(second: int, player: Player, replay: Replay) -> int:

    larvae = set([
        event.unit
        for event
        in replay.events
        if (event.name in ["UnitBornEvent", "UnitDoneEvent"] and
            event.unit.owner == player and
            event.unit.name == "Larva" )
        ])

    larvae_started_times = [int(larva.started_at / (1.4 * replay.game_fps)) for larva in larvae]
    return len([time for time in larvae_started_times if time < second])


if __name__ == '__main__':
    main()