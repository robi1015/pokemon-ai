# gunshi/image_utils.py
# -*- coding: utf-8 -*-
from PIL import Image, ImageEnhance, ImageFilter

def enhance_for_switch_selection(img: Image.Image, scale: int = 2) -> Image.Image:
    img = img.convert("RGB")
    if scale >= 2:
        img = img.resize((img.width * scale, img.height * scale), Image.BICUBIC)
    img = ImageEnhance.Contrast(img).enhance(1.45)
    img = ImageEnhance.Sharpness(img).enhance(1.9)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=170, threshold=3))
    return img

def crop_ratio(img: Image.Image, left: float, top: float, right: float, bottom: float) -> Image.Image:
    W, H = img.size
    l = int(W * max(0.0, min(1.0, left)))
    t = int(H * max(0.0, min(1.0, top)))
    r = int(W * max(0.0, min(1.0, right)))
    b = int(H * max(0.0, min(1.0, bottom)))
    if r <= l + 10 or b <= t + 10:
        return img
    return img.crop((l, t, r, b))

def auto_crop_switch_selection(img: Image.Image) -> Image.Image:
    return crop_ratio(img, left=0.08, top=0.12, right=0.92, bottom=0.92)
