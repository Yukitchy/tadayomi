#!/usr/bin/env python3
"""OGP画像 og4.png を生成する。 python3 og.py
左=ロゴ(assets/logo.png)、右=キャッチ(中央)＋試作版表記、下=ティール帯(横断の一文)。
揃え: ロゴ左端=帯文字の左端(X0)／キャッチ=ブロック(長い行の幅)を右カラム(ロゴ右〜XR)×帯より上の中央に置き、行は左揃え／試作版表記の字面下端=マスコット足元。"""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).parent
W, H, BAND = 1200, 630, 70          # 帯は現行と同じ 560〜630
TEAL, TEAL_D, INK = (0, 151, 160), (0, 115, 122), (26, 26, 26)
X0, XR = 80, 1120                   # 左右の版面
FOOT = 217                          # logo.png 字面内でマスコットとロゴタイプの境の行
F = "/System/Library/Fonts/ヒラギノ角ゴシック W{}.ttc"

def font(w, s): return ImageFont.truetype(F.format(w), s)

def ink_bbox(im):
    d = ImageChops.difference(im, Image.new("RGB", im.size, "white")).convert("L")
    return d.point(lambda v: 255 if v > 24 else 0).getbbox()

def build():
    logo = Image.open(ROOT / "assets/logo.png").convert("RGB")
    logo = logo.crop(ink_bbox(logo))
    LH = 452                                    # ロゴの字面高さ（現行約433→拡大）
    s = LH / logo.height
    logo = logo.resize((round(logo.width * s), LH), Image.LANCZOS)
    top = (H - BAND - LH) // 2
    foot = top + round(FOOT * s)                # マスコット足元（ロゴタイプとの隙間）

    im = Image.new("RGB", (W, H), "white")
    im.paste(logo, (X0, top))
    d = ImageDraw.Draw(im)
    x = X0 + logo.width + 40                    # 右カラム左端

    # キャッチ: 右カラム幅に収まる最大サイズで、右カラム×帯より上の中央に（上下左右とも字面中央）
    lines = ["いま無料の漫画が", "すぐにわかる。"]
    size = 80
    while max(font(8, size).getlength(l) for l in lines) > XR - x: size -= 1
    fc = font(8, size)
    lead = round(size * 1.36)
    cx, cy = (x + XR) / 2, (H - BAND) / 2
    t = fc.getbbox(lines[0])[1]; b = lead * (len(lines) - 1) + fc.getbbox(lines[-1])[3]
    y = cy - (t + b) / 2
    lx = cx - max(fc.getlength(l) for l in lines) / 2   # 2行の左端を揃える
    for i, l in enumerate(lines): d.text((lx, y + i * lead), l, font=fc, fill=INK, anchor="la")

    # 試作版の表記: マスコット足元付近。中央のキャッチと重なるため、キャッチの直下に同じ中心軸で置く
    sub = "タダヨミ 試作版"
    fs = font(7, round(size * 0.56))
    sy = y + b + round(size * 0.6) - fs.getbbox(sub, anchor="ma")[1]
    d.text((cx, sy), sub, font=fs, fill=TEAL_D, anchor="ma")

    # 帯: 横断の一文を白字で
    d.rectangle([0, H - BAND, W, H], fill=TEAL)
    fb = font(7, 24)
    d.text((X0, H - BAND / 2), "電子書店＋出版社Webを横断", font=fb, fill="white", anchor="lm")
    im.save(ROOT / "og4.png", optimize=True)
    return dict(logo_w=logo.width, top=top, foot=foot, x=x, size=size, lx=round(lx))

if __name__ == "__main__":
    r = build()
    assert r["size"] >= 57, r   # キャッチが現行(約54px)より大きいこと
    print(r)
