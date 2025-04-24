from pathlib import Path
import json, re, sys, math, configparser

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

def osu_to_simple(path, columns=8):
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
            lane = int(int(x) // lane_width) + 1          # 1-based (sorry)
            t = int(t)
            typ = int(typ)
            duration = 0
            if typ & 128:                                 # hold
                end = int(line.split(',')[5].split(':')[0])
                duration = end - t
            out.append(
                dict(id=note_id, lane=lane,
                     time=t, duration=duration, judgment="")
            )
            note_id += 1
    song_end = max(n['time'] + n['duration'] for n in out)
    return {"notes": out, "end": song_end + 2000, "audio": audio, "offset": -offset} # end 2 secs after

if __name__ == "__main__":
    chart = osu_to_simple(sys.argv[1])            # python osurip.py song.osu
    out_path = Path(sys.argv[2]).with_suffix('.chart')

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2)
    print("Wrote ", out_path)