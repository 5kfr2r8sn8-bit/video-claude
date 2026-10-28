#!/usr/bin/env python3
"""Edit asas video TikTok: potong jeda senyap, sari kata dan tajuk hook.

Dua langkah, supaya sari kata boleh disemak sebelum dibakar ke video:

  prepare  video -> build/<nama>/cut.mp4 (jeda senyap dipotong, 9:16, audio dinormalkan)
                    build/<nama>/subs.srt (transkrip automatik)
  render   build/<nama> -> final/<nama>.mp4 (sari kata + tajuk hook dibakar)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

W, H = 1080, 1920
SR = 16000
MODELS = Path(os.environ.get("TIKTOK_MODELS", Path.home() / ".cache/tiktok-edit/models"))


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return float(out.strip())


# ---------- potong jeda senyap ----------

def detect_silences(path, noise_db, min_silence):
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
         "-af", f"silencedetect=n={noise_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def keep_segments(duration, silences, pad, min_keep=0.15):
    keep, cursor = [], 0.0
    for s, e in silences:
        s = max(s, 0.0)
        if s > cursor:
            keep.append((cursor, s))
        cursor = duration if e is None else e
    if cursor < duration:
        keep.append((cursor, duration))

    merged = []
    for a, b in keep:
        a, b = max(0.0, a - pad), min(duration, b + pad)
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return [(a, b) for a, b in merged if b - a >= min_keep]


def reframe_filter(fit):
    if fit == "blur":
        return (f"split[bg0][fg0];"
                f"[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:5[bg];"
                f"[fg0]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"


def cut_video(src, dst, segments, fit, workdir):
    parts = []
    for i, (a, b) in enumerate(segments):
        parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}];")
    pairs = "".join(f"[v{i}][a{i}]" for i in range(len(segments)))
    parts.append(f"{pairs}concat=n={len(segments)}:v=1:a=1[vc][ac];")
    parts.append(f"[vc]{reframe_filter(fit)}[vout];")
    parts.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    script = workdir / "cut.filter"
    script.write_text("\n".join(parts))
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
         "-filter_complex_script", str(script), "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", str(dst)])


# ---------- transkripsi ----------

def load_audio(path):
    import numpy as np
    raw = run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
               "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def transcribe(path, lang, model, threads):
    import numpy as np
    import sherpa_onnx

    mdir = MODELS / f"sherpa-onnx-whisper-{model}"
    enc = mdir / f"{model}-encoder.int8.onnx"
    if not enc.exists() or not (MODELS / "silero_vad.onnx").exists():
        sys.exit(f"Model tiada di {MODELS}. Jalankan dulu: scripts/setup_models.sh {model}")

    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(enc), decoder=str(mdir / f"{model}-decoder.int8.onnx"),
        tokens=str(mdir / f"{model}-tokens.txt"), language=lang, task="transcribe",
        num_threads=threads)

    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = str(MODELS / "silero_vad.onnx")
    cfg.silero_vad.min_silence_duration = 0.1
    cfg.silero_vad.min_speech_duration = 0.2
    cfg.silero_vad.max_speech_duration = 8
    cfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)

    samples = load_audio(path)
    win = cfg.silero_vad.window_size
    speech = []

    def drain():
        while not vad.empty():
            seg = vad.front
            speech.append((seg.start / SR, np.asarray(seg.samples, dtype=np.float32)))
            vad.pop()

    for i in range(0, len(samples), win):
        vad.accept_waveform(samples[i:i + win])
        drain()
    vad.flush()
    drain()

    lines = []
    for n, (start, audio) in enumerate(speech, 1):
        stream = rec.create_stream()
        stream.accept_waveform(SR, audio)
        rec.decode_stream(stream)
        text = stream.result.text.strip()
        print(f"  [{n}/{len(speech)}] {start:6.2f}s  {text}", flush=True)
        if text:
            lines.append((start, start + len(audio) / SR, text))
    return lines


def split_captions(lines, max_words, max_chars):
    """Pecahkan setiap ayat kepada kapsyen pendek; masa diagih ikut panjang aksara."""
    caps = []
    for start, end, text in lines:
        chunks, cur = [], []
        for w in text.split():
            if cur and (len(cur) >= max_words or len(" ".join(cur + [w])) > max_chars):
                chunks.append(" ".join(cur))
                cur = []
            cur.append(w)
        if cur:
            chunks.append(" ".join(cur))
        total = sum(len(c) + 1 for c in chunks)
        t = start
        for c in chunks:
            d = (end - start) * (len(c) + 1) / total
            caps.append((t, t + d, c))
            t += d
    return caps


# ---------- SRT / ASS ----------

def srt_time(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def write_srt(caps, path):
    path.write_text("".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n\n"
                            for i, (a, b, t) in enumerate(caps, 1)), encoding="utf-8")


def read_srt(path):
    caps = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        rows = block.strip().splitlines()
        tline = next((r for r in rows if "-->" in r), None)
        if not tline:
            continue
        a, b = (sum(float(x) * m for x, m in zip(p.strip().replace(",", ".").split(":"), (3600, 60, 1)))
                for p in tline.split("-->"))
        text = " ".join(rows[rows.index(tline) + 1:]).strip()
        if text:
            caps.append((a, b, text))
    return caps


def ass_time(t):
    cs = round(max(t, 0) * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}"


def ass_escape(text):
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def write_ass(caps, hook, hook_secs, duration, upper, font, path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},86,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,90,90,560,1
Style: Hook,{font},74,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,20,0,8,80,80,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    if hook:
        wrapped = r"\N".join(textwrap.wrap(ass_escape(hook), 22))
        end = duration if hook_secs <= 0 else min(hook_secs, duration)
        events.append(f"Dialogue: 1,{ass_time(0)},{ass_time(end)},Hook,,0,0,0,,{{\\fad(150,150)}}{wrapped}")
    pop = r"{\fscx112\fscy112\t(0,90,\fscx100\fscy100)}"
    for a, b, t in caps:
        t = ass_escape(t.upper() if upper else t)
        events.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Caption,,0,0,0,,{pop}{t}")
    path.write_text(head + "\n".join(events) + "\n", encoding="utf-8")


# ---------- arahan ----------

def cmd_prepare(args):
    src = Path(args.video).resolve()
    work = Path(args.work or Path("build") / src.stem).resolve()
    work.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(src)
    if args.no_cut:
        segments = [(0.0, duration)]
    else:
        silences = detect_silences(src, args.silence_db, args.min_silence)
        segments = keep_segments(duration, silences, args.pad)
        if not segments:
            sys.exit("Tiada bahagian bersuara dikesan. Cuba --silence-db yang lebih rendah, cth -45.")
    kept = sum(b - a for a, b in segments)
    print(f"Asal {duration:.1f}s -> {kept:.1f}s ({len(segments)} segmen, buang {duration - kept:.1f}s senyap)")

    cut = work / "cut.mp4"
    cut_video(src, cut, segments, args.fit, work)

    if args.no_subs:
        caps = []
    else:
        print("Transkripsi ...")
        lines = transcribe(cut, args.lang, args.model, args.threads)
        caps = split_captions(lines, args.max_words, args.max_chars)
    write_srt(caps, work / "subs.srt")

    (work / "meta.json").write_text(json.dumps({
        "source": str(src), "duration_in": duration, "duration_out": probe_duration(cut),
        "segments": segments, "fit": args.fit, "lang": args.lang}, indent=2))
    print(f"\nSiap: {cut}\nSari kata (semak/betulkan): {work / 'subs.srt'}")


def cmd_render(args):
    work = Path(args.work).resolve()
    meta = json.loads((work / "meta.json").read_text())
    cut = work / "cut.mp4"
    caps = [] if args.no_subs else read_srt(work / "subs.srt")
    write_ass(caps, args.hook, args.hook_secs, meta["duration_out"], args.upper, args.font,
              work / "overlay.ass")

    out = Path(args.out or Path("final") / f"{Path(meta['source']).stem}_tiktok.mp4").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(cut),
         "-vf", "ass=overlay.ass", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out)], cwd=work)
    print(f"Video akhir: {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("prepare", help="potong senyap, format 9:16, transkrip")
    pr.add_argument("video")
    pr.add_argument("--work", help="folder kerja (lalai: build/<nama video>)")
    pr.add_argument("--silence-db", type=float, default=-35, help="paras dianggap senyap (dB)")
    pr.add_argument("--min-silence", type=float, default=0.35, help="jeda minimum untuk dipotong (s)")
    pr.add_argument("--pad", type=float, default=0.08, help="ruang dikekalkan di tepi suara (s)")
    pr.add_argument("--fit", choices=["crop", "blur"], default="crop",
                    help="crop = penuhkan skrin; blur = video penuh atas latar kabur")
    pr.add_argument("--lang", default="ms", help="kod bahasa Whisper (ms, en, id ...)")
    pr.add_argument("--model", default="small")
    pr.add_argument("--threads", type=int, default=os.cpu_count() or 4)
    pr.add_argument("--max-words", type=int, default=3)
    pr.add_argument("--max-chars", type=int, default=18)
    pr.add_argument("--no-cut", action="store_true")
    pr.add_argument("--no-subs", action="store_true")
    pr.set_defaults(func=cmd_prepare)

    rd = sub.add_parser("render", help="bakar sari kata + hook ke video akhir")
    rd.add_argument("work", help="folder kerja dari langkah prepare")
    rd.add_argument("--hook", default="", help="teks tajuk hook di bahagian atas")
    rd.add_argument("--hook-secs", type=float, default=0, help="tempoh hook (0 = sepanjang video)")
    rd.add_argument("--out", help="fail output (lalai: final/<nama>_tiktok.mp4)")
    rd.add_argument("--upper", action="store_true", help="sari kata huruf besar")
    rd.add_argument("--font", default="Inter")
    rd.add_argument("--no-subs", action="store_true")
    rd.set_defaults(func=cmd_render)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
