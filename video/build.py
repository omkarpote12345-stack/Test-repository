import os, subprocess, wave, sys
from PIL import Image, ImageDraw, ImageFont
from scenes import SCENES

W, H = 1280, 720
SPEED = int(os.environ.get("SPEED", 135))
GAP = 0.45          # silence after each sentence (s)
TAIL = 1.2          # extra hold at end of each scene (s)
OUT = "/tmp/vbuild"; os.makedirs(OUT, exist_ok=True)
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
f = lambda p, s: ImageFont.truetype(p, s)
BG1, BG2 = (18, 24, 48), (46, 28, 84)
ACC, TXT, DIM = (255, 196, 61), (245, 247, 255), (170, 178, 205)
CARD = (58, 66, 110)

def bg():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(BG1[i] + (BG2[i]-BG1[i])*t) for i in range(3)))
    return im

def wrap(d, text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def center(d, y, text, font, fill):
    d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)

def draw(scene, idx, nvis, caption, progress):
    im = bg(); d = ImageDraw.Draw(im)
    lay, items = scene["layout"], scene["items"]
    if lay == "hero":
        tl = wrap(d, scene["title"], f(B, 76), W - 160)
        y = 150
        for l in tl: center(d, y, l, f(B, 76), ACC); y += 92
        y += 30
        for i, it in enumerate(items[:nvis]):
            for l in wrap(d, it, f(B if i == 0 else R, 40 if i == 0 else 28), W - 160):
                center(d, y, l, f(B if i == 0 else R, 40 if i == 0 else 28), TXT if i == 0 else DIM); y += 54
            y += 14
    else:
        d.text((70, 60), scene["title"], font=f(B, 52), fill=ACC)
        d.rectangle([70, 128, 220, 132], fill=ACC)
        if lay == "bullets":
            y = 190
            for it in items[:nvis]:
                d.ellipse([80, y + 18, 98, y + 36], fill=ACC)
                for l in wrap(d, it, f(R, 40), W - 220):
                    d.text((120, y), l, font=f(R, 40), fill=TXT); y += 56
                y += 36
        elif lay == "compare":
            for i, it in enumerate(items[:nvis]):
                a, b = it.split("|"); x = 70 + i * 600
                d.rounded_rectangle([x, 190, x + 540, 470], 24, fill=CARD, outline=ACC if i else DIM, width=3)
                yy = 215
                for l in wrap(d, a, f(B, 32), 480): d.text((x + 30, yy), l, font=f(B, 32), fill=TXT); yy += 44
                yy += 20
                for l in wrap(d, b, f(R, 28), 480): d.text((x + 30, yy), l, font=f(R, 28), fill=ACC if i else DIM); yy += 38
        elif lay == "steps":
            for i, it in enumerate(items[:nvis]):
                a, b = it.split("|"); x = 70 + (i % 3) * 395; y = 155 + (i // 3) * 190
                d.rounded_rectangle([x, y, x + 365, y + 172], 20, fill=CARD, outline=ACC, width=3)
                d.text((x + 24, y + 8), a[0], font=f(B, 56), fill=ACC)
                d.text((x + 24, y + 80), a, font=f(B, 30), fill=TXT)
                for k, l in enumerate(wrap(d, b, f(R, 24), 320)): d.text((x + 24, y + 124 + k*30), l, font=f(R, 24), fill=DIM)
        elif lay == "stats":
            for i, it in enumerate(items[:nvis]):
                a, b = it.split("|"); x = 70 + i * 395
                d.rounded_rectangle([x, 190, x + 365, 450], 20, fill=CARD, outline=ACC, width=3)
                d.text((x + (365 - d.textlength(a, font=f(B, 80))) / 2, 240), a, font=f(B, 80), fill=ACC)
                d.text((x + (365 - d.textlength(b, font=f(R, 36))) / 2, 350), b, font=f(R, 36), fill=TXT)
            d.text((70, 480), "Figures as cited in the podcast episode", font=f(R, 22), fill=DIM)
    # caption bar
    cl = wrap(d, caption, f(R, 28), W - 120)[:3]
    top = H - 36 - 44 * len(cl) - 18
    d.rectangle([0, top, W, H - 14], fill=(10, 12, 28))
    for k, l in enumerate(cl): center(d, top + 12 + 44 * k, l, f(R, 28), TXT)
    d.rectangle([0, H - 8, int(W * progress), H], fill=ACC)
    im.save(f"{OUT}/f{idx:03d}.png")

def tts(text, path):
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", str(SPEED), "-p", "45", "-w", path, text], check=True)

def silence(n, params):
    return b"\x00" * (int(params.framerate * n) * params.sampwidth * params.nchannels)

frames, pcm, params, total_n = [], b"", None, sum(len(s["sents"]) for s in SCENES)
k = 0
for si, sc in enumerate(SCENES):
    for ti, (text, nvis) in enumerate(sc["sents"]):
        p = f"{OUT}/a{k:03d}.wav"; tts(text, p)
        with wave.open(p) as w:
            params = w.getparams(); data = w.readframes(w.getnframes()); dur = w.getnframes() / w.getframerate()
        gap = GAP + (TAIL if ti == len(sc["sents"]) - 1 else 0)
        pcm += data + silence(gap, params)
        draw(sc, k, nvis, text, (k + 1) / total_n)
        frames.append((f"{OUT}/f{k:03d}.png", dur + gap)); k += 1
with wave.open(f"{OUT}/all.wav", "wb") as w:
    w.setparams(params); w.writeframes(pcm)
total = sum(d for _, d in frames)
print(f"total {total:.1f}s = {int(total//60)}:{int(total%60):02d}")
if "--dry" in sys.argv: sys.exit()
with open(f"{OUT}/list.txt", "w") as fh:
    for p, d in frames: fh.write(f"file '{p}'\nduration {d:.3f}\n")
    fh.write(f"file '{frames[-1][0]}'\n")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-i", f"{OUT}/all.wav",
  "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-c:a", "aac", "-b:a", "128k",
  "-movflags", "+faststart", "-shortest", "boring-products-go-viral.mp4"], check=True)
print("done")
