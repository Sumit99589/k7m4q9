"""Render a narrated screen walkthrough from captured application screens.

Uses Pillow, edge-tts, ffmpeg, ffprobe, and DejaVu Sans font.
Outputs a local MP4, SRT captions, and timing manifest.
Audio voice: High-fidelity British English Neural voice (en-GB-RyanNeural).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import wave
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = Path('/usr/share/fonts/truetype/dejavu')
W, H = 1920, 1080


def font(size: int, bold=False):
    return ImageFont.truetype(str(FONT / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)


def wrap(draw, text, f, max_width):
    lines = []
    line = ''
    for word in text.split():
        candidate = f'{line} {word}'.strip()
        if line and draw.textlength(candidate, font=f) > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def textblock(draw, text, x, y, width, size, fill, bold=False, gap=1.45):
    f = font(size, bold)
    for line in wrap(draw, text, f, width):
        draw.text((x, y), line, font=f, fill=fill)
        y += int(size * gap)
    return y


def timestamp(seconds):
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    secs, millis = divmod(millis, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02},{millis:03}'


def make_frame(scene, index, total, path):
    im = Image.new('RGB', (W, H), '#edf2ef')
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, W, 78), fill='#12363d')
    draw.text((34, 22), 'windward', font=font(27, True), fill='#f4f7f4')
    part = 'PART 1  /  CUSTOMER PILOT' if scene['part'] == 1 else 'PART 2  /  TECHNICAL REVIEW'
    draw.text((240, 28), part, font=font(19, True), fill='#a6cfc4')
    draw.text((1735, 27), f'{index:02} / {total:02}', font=font(19), fill='#d7e9e3')
    image = Image.open(ROOT / 'demo/screens' / scene['image']).convert('RGB')
    if scene['part'] == 1:
        top = min(scene.get('crop_top', 0), max(0, image.height - 900))
        image = image.crop((0, top, image.width, min(image.height, top + 900)))
    maxw, maxh = 1450, 910
    scale = min(maxw / image.width, maxh / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    x = 24 + (maxw - image.width) // 2
    y = 96 + (maxh - image.height) // 2
    draw.rounded_rectangle((22, 94, 1478, 1010), radius=12, fill='white', outline='#ceddd5', width=2)
    im.paste(image, (x, y))
    x = 1510
    y = 118
    y = textblock(draw, scene['title'], x, y, 365, 30, '#16393d', True, 1.25)
    y += 35
    draw.rectangle((x, y, x + 58, y + 4), fill='#bd9351')
    y += 30
    y = textblock(draw, scene['takeaway'], x, y, 365, 23, '#28665d', True, 1.4)
    y += 30
    y = textblock(draw, scene['note'], x, y, 365, 21, '#4e6669', False, 1.5)
    draw.rounded_rectangle((1510, 906, 1883, 1008), radius=10, fill='#faedce')
    textblock(draw, 'Live Elexon WINDFOR + FUELHH Analysis · January 2026', 1528, 922, 338, 18, '#795c25', True, 1.4)
    draw.rectangle((0, 1030, W, H), fill='#12363d')
    draw.text((30, 1045), 'Windward · UK Day-Ahead Renewable Generation Intelligence · Elexon BMRS Live Data', font=font(17), fill='#dae7e3')
    im.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'demo' / 'windward-walkthrough.mp4')
    parser.add_argument('--prepare-only', action='store_true', help='Create inputs and command without running ffmpeg')
    args = parser.parse_args()
    scenes = json.loads((ROOT / 'demo/storyboard.json').read_text())
    render = ROOT / 'demo/render'
    render.mkdir(parents=True, exist_ok=True)
    audio_chunks = []
    timings = []
    subtitle_entries = []
    cursor = 0.0
    subtitle_index = 1
    sample_rate = None
    edge_tts_bin = str(ROOT / '.venv' / 'bin' / 'edge-tts')

    for i, scene in enumerate(scenes, 1):
        text = render / f'{i:02d}.txt'
        text.write_text(scene['narration'])
        mp3 = render / f'{i:02d}.mp3'
        wav = render / f'{i:02d}.wav'

        # Generate neural audio using edge-tts
        subprocess.run([edge_tts_bin, '--voice', 'en-GB-RyanNeural', '--text', scene['narration'], '--write-media', str(mp3)], check=True)
        # Convert to mono 24kHz 16-bit PCM WAV
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp3), '-ac', '1', '-ar', '24000', str(wav)], check=True)

        with wave.open(str(wav), 'rb') as reader:
            rate = reader.getframerate()
            channels = reader.getnchannels()
            width = reader.getsampwidth()
            audio = reader.readframes(reader.getnframes())

        if channels != 1 or width != 2:
            raise ValueError('Expected mono 16-bit WAV output')
        if sample_rate is not None and sample_rate != rate:
            raise ValueError('Sample rates differ')
        sample_rate = rate
        spoken = len(audio) / (rate * 2)
        lead = 0.25
        trail = 0.70
        audio_chunks.append(b'\x00\x00' * round(lead * rate) + audio + b'\x00\x00' * round(trail * rate))
        duration = len(audio_chunks[-1]) / (rate * 2)

        make_frame(scene, i, len(scenes), render / f'{i:02d}.png')
        timings.append({
            'scene': i,
            'part': scene['part'],
            'title': scene['title'],
            'start_seconds': round(cursor, 3),
            'duration_seconds': round(duration, 3)
        })

        words = scene['narration'].split()
        chunks = [words[j:j + 15] for j in range(0, len(words), 15)]
        weights = [sum(len(w) + 1 for w in chunk) for chunk in chunks]
        total_weight = sum(weights)
        used = 0
        for chunk, weight in zip(chunks, weights):
            start = cursor + lead + spoken * used / total_weight
            end = cursor + lead + spoken * (used + weight) / total_weight
            caption = ' '.join(chunk)
            if len(caption) > 72:
                middle = len(chunk) // 2
                caption = ' '.join(chunk[:middle]) + '\n' + ' '.join(chunk[middle:])
            subtitle_entries.append(f'{subtitle_index}\n{timestamp(start)} --> {timestamp(end)}\n{caption}\n')
            used += weight
            subtitle_index += 1
        cursor += duration

    totals = {part: sum(t['duration_seconds'] for t in timings if t['part'] == part) for part in (1, 2)}
    print(f'Part 1: {totals[1]:.1f}s, Part 2: {totals[2]:.1f}s, Total: {cursor:.1f}s')
    if max(totals.values()) > 300 or cursor > 600:
        raise ValueError(f'Video exceeds required duration: {totals}, total={cursor}')

    with wave.open(str(render / 'narration.wav'), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(b''.join(audio_chunks))

    (ROOT / 'demo/captions.srt').write_text('\n'.join(subtitle_entries))
    manifest = {
        'duration_seconds': round(cursor, 3),
        'parts_seconds': totals,
        'voice': 'Microsoft Neural en-GB-RyanNeural',
        'data': 'Real Elexon BMRS WINDFOR and FUELHH stream data for January 2026',
        'screen_source': 'Actual application and review-page captures',
        'caption_timing': 'Synchronized SRT captions',
        'chapters': timings
    }
    (ROOT / 'demo/timing.json').write_text(json.dumps(manifest, indent=2))

    concat = 'ffconcat version 1.0\n'
    for t in timings:
        concat += f"file '{t['scene']:02d}.png'\nduration {t['duration_seconds']:.3f}\n"
    concat += f"file '{len(scenes):02d}.png'\n"
    (render / 'frames.ffconcat').write_text(concat)

    meta = ';FFMETADATA1\ntitle=Windward - Customer and engineering walkthrough\ncomment=Real Elexon WINDFOR and FUELHH/WIND observations for January 2026.\n'
    for part in (1, 2):
        start = next(t['start_seconds'] for t in timings if t['part'] == part)
        end = start + totals[part]
        meta += f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(start * 1000)}\nEND={round(end * 1000)}\ntitle=Part {part} - ' + (
            'Customer pilot' if part == 1 else 'Technical review'
        ) + '\n'
    (render / 'chapters.ffmeta').write_text(meta)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'ffmpeg', '-hide_banner', '-y',
        '-f', 'concat', '-safe', '0', '-i', str(render / 'frames.ffconcat'),
        '-i', str(render / 'narration.wav'),
        '-i', str(ROOT / 'demo/captions.srt'),
        '-i', str(render / 'chapters.ffmeta'),
        '-map', '0:v:0', '-map', '1:a:0', '-map', '2:s:0',
        '-map_metadata', '3', '-map_chapters', '3',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'stillimage',
        '-crf', '22', '-pix_fmt', 'yuv420p', '-r', '10',
        '-c:a', 'aac', '-b:a', '96k',
        '-c:s', 'mov_text', '-metadata:s:s:0', 'language=eng',
        '-t', f'{cursor:.3f}', '-movflags', '+faststart', str(args.output)
    ]
    (render / 'ffmpeg-command.json').write_text(json.dumps(cmd, indent=2))
    if not args.prepare_only:
        subprocess.run(cmd, check=True)
    print(json.dumps({'duration_seconds': cursor, 'part_seconds': totals, 'output': str(args.output), 'encoded': not args.prepare_only}, indent=2))


if __name__ == '__main__':
    main()
