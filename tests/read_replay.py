
import sys
import sc2reader

if len(sys.argv) != 2:
    print("Usage: python read_replay.py file.SC2Replay")
    raise SystemExit(1)

replay = sc2reader.load_replay(
    sys.argv[1],
    load_level=4
)

print("Map:", replay.map_name)
print("Duration:", replay.game_length)
print("Players:")

for player in replay.players:
    print(
        player.name,
        player.pick_race,
        player.result
    )

print("Events:", len(replay.events))

