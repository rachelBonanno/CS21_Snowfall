# osurip.py
# CS21 Concurrent Programming
# Final Project -- Snowfall
# Team Snowfall -- Stephanie Wilson, Rachel Bonanno, Justin Millette
# 4/28/25
#
# This file is a script that takes in a .osu file, and produces a .chart file
# formatted for use in the game Snowfall. Some of this code was modified based
# on a osu! forum post for parsing .osu files.
#
# Usage: python osurip.py song.osu /path/to/output.chart

from pathlib import Path
import json, sys

def get_general_tags(path):
    audio = None
    lead  = 0
    inside = False
    with open(path, encoding='utf8') as f:
        for line in f:
            if line.startswith('[General]'):
                inside = True
                continue
            if inside:
                if line.startswith('['):   # next section
                    break
                if line.startswith('AudioFilename:'):
                    audio = line.split(':',1)[1].strip()
                elif line.startswith('AudioLeadIn:'):
                    lead = int(line.split(':',1)[1])
    return audio, lead

def osu_to_chart(path, columns=8):
    out, note_id = [], 0
    lane_width = 512 / columns
    audio, offset = get_general_tags(path)
    with open(path, encoding='utf8') as f:
        hitobjects = False
        for line in f:
            if line.startswith('[HitObjects]'):
                hitobjects = True
                continue
            if not hitobjects or not line.strip():
                continue
            x, y, t, typ, *_rest = line.split(',')[:5]
            # for some reason, since osu!standard is a game where notes have 
            # x and y positions, the notes in osu!mania (the vertical-scrolling
            # rhythm game version) also have x positions.
            # we divide them up into our lanes here
            lane = int(int(x) // lane_width) + 1          # 1-based (sorry)
            t = int(t)
            typ = int(typ)
            duration = 0
            if typ & 128:                                 # hold note
                end = int(line.split(',')[5].split(':')[0])
                duration = end - t
            out.append(
                dict(id=note_id, lane=lane,
                     time=t, duration=duration, judgment="")
            )
            note_id += 1
    song_end = max(n['time'] + n['duration'] for n in out)
    return {"notes": out, "end": song_end + 2000,  # end 2 secs after
            "audio": audio, "offset": -offset}

if __name__ == "__main__":
    # python osurip.py song.osu /path/to/output.chart
    chart = osu_to_chart(sys.argv[1])            
    out_path = Path(sys.argv[2]).with_suffix('.chart')

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2)
    print("Wrote ", out_path)