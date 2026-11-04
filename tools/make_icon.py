"""Render assets/icon.png (256), icon-1024.png (master) and icon.ico. Run once; output is committed."""
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024


def gradient(size, c1, c2):
    base = Image.new("RGB", (size, size), c1)
    top = Image.new("RGB", (size, size), c2)
    v = Image.linear_gradient("L").resize((size, size))
    mask = Image.blend(v, v.rotate(90), 0.5)
    return Image.composite(top, base, mask)


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg = gradient(S, (37, 99, 235), (14, 165, 164)).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([40, 40, S - 40, S - 40], radius=230, fill=255)
    img.paste(bg, (0, 0), mask)

    # phone body with soft shadow
    x0, y0, x1, y1 = 300, 150, 724, 874
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([x0 + 14, y0 + 24, x1 + 14, y1 + 24], radius=86, fill=(10, 30, 80, 100))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(20)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=86, fill=(255, 255, 255, 255))
    d.rounded_rectangle([x0 + 30, y0 + 30, x1 - 30, y1 - 30], radius=60, fill=(232, 240, 255, 255))
    d.rounded_rectangle([462, y0 + 52, 562, y0 + 80], radius=14, fill=(23, 32, 54, 255))  # dynamic island

    # photo on screen: sky, sun, mountains (drawn big then downsampled for clean edges)
    big = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0))
    b = ImageDraw.Draw(big)
    px0, py0, px1, py1 = 2 * (x0 + 62), 2 * 300, 2 * (x1 - 62), 2 * 610
    b.rounded_rectangle([px0, py0, px1, py1], radius=56, fill=(147, 197, 253, 255))
    b.ellipse([px1 - 250, py0 + 70, px1 - 110, py0 + 210], fill=(253, 224, 71, 255))
    b.polygon([(px0, py1), (px0 + 230, py0 + 260), (px0 + 430, py1)], fill=(37, 99, 235, 255))
    b.polygon([(px0 + 250, py1), (px0 + 500, py0 + 330), (px1, py1)], fill=(14, 165, 164, 255))
    clip = Image.new("L", (S * 2, S * 2), 0)
    ImageDraw.Draw(clip).rounded_rectangle([px0, py0, px1, py1], radius=56, fill=255)
    photo = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0))
    photo.paste(big, (0, 0), clip)
    img = Image.alpha_composite(img, photo.resize((S, S), Image.LANCZOS))

    # download arrow below the photo
    big = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0))
    b = ImageDraw.Draw(big)
    cx = 2 * 512
    b.rounded_rectangle([cx - 34, 2 * 645, cx + 34, 2 * 760], radius=34, fill=(37, 99, 235, 255))
    b.polygon([(cx - 120, 2 * 720), (cx + 120, 2 * 720), (cx, 2 * 815)], fill=(37, 99, 235, 255))
    img = Image.alpha_composite(img, big.resize((S, S), Image.LANCZOS))

    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    img.save(os.path.join(ROOT, "assets", "icon-1024.png"))
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(ROOT, "assets", "icon.png"))
    img.save(os.path.join(ROOT, "assets", "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icons written to assets/")


if __name__ == "__main__":
    main()
