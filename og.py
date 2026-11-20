#!/usr/bin/env python3
"""OGP画像 og2.png を生成する。 python3 og.py
左=ロゴ(assets/logo.png)、右=キャッチ＋横断の一文、下=ティール帯。
揃え: ロゴ左端=帯文字の左端(X0)／キャッチ右端=XR(左右余白80)／キャッチ1行目の字面上端=マスコット頭頂／横断の一文の字面下端=マスコット足元。"""
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

    # キャッチ: 右カラム幅いっぱいに収まる最大サイズ
    lines = ["いま無料の漫画を", "終了が近い順に。"]
    size = 80
    while max(font(8, size).getlength(l) for l in lines) > XR - x: size -= 1
    fc = font(8, size)
    lead = round(size * 1.36)
    y = top - fc.getbbox(lines[0])[1]           # 字面上端を頭頂に
    for i, l in enumerate(lines): d.text((x, y + i * lead), l, font=fc, fill=INK)

    # 横断の一文: 字面下端をマスコット足元に
    sub = "電子書店＋出版社Webを横断"
    fs = font(7, round(size * 0.56))
    d.text((x, foot - fs.getbbox(sub)[3]), sub, font=fs, fill=TEAL_D)

    # 帯（現行どおり）
    d.rectangle([0, H - BAND, W, H], fill=TEAL)
    fb = font(7, 24)
    d.text((X0, H - BAND / 2), "タダヨミ 試作版", font=fb, fill="white", anchor="lm")
    im.save(ROOT / "og2.png", optimize=True)
    return dict(logo_w=logo.width, top=top, foot=foot, x=x, size=size)

if __name__ == "__main__":
    r = build()
    assert r["size"] >= 57, r   # キャッチが現行(約54px)より大きいこと
    print(r)
