"""Render the skin's board and stone textures (development-time; needs numpy and Pillow).

The rendered PNG files are committed, so neither KaTrain nor the installer
needs these libraries. Run again only to change the look:

    python scripts/build_skin_assets.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parents[1] / 'plugins' / 'katrain'


def save(name, array):
    Image.fromarray(np.clip(array * 255, 0, 255).astype(np.uint8)).save(OUT / name, optimize=True)
    print(name, array.shape)


def smooth_noise(rng, length, scale):
    """1-D value noise, linearly interpolated from `length / scale` random knots."""
    knots = rng.random(int(length / scale) + 3)
    position = np.arange(length) / scale
    index = position.astype(int)
    blend = position - index
    blend = blend * blend * (3 - 2 * blend)
    return knots[index] * (1 - blend) + knots[index + 1] * blend


def board(size=768, seed=7):
    """Straight-grained kaya: fine vertical grain with slow drift, lit from the upper left."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    drift = (smooth_noise(rng, size, 190)[:, None] - .5) * 26 + (smooth_noise(rng, size, 60)[:, None] - .5) * 5
    u = x + drift
    grain = np.zeros((size, size))
    for scale, weight in ((46, .50), (17, .30), (6, .14), (2.3, .06)):
        row = smooth_noise(rng, size * 2, scale)
        grain += weight * row[np.clip(u.astype(int) + size // 2, 0, size * 2 - 1)]
    rings = .5 + .5 * np.sin(u / 9.5 + 5 * smooth_noise(rng, size * 2, 120)[np.clip(u.astype(int) + size // 2, 0, size * 2 - 1)])
    grain = .72 * grain + .28 * rings
    fibre = rng.random((size, size))
    fibre = np.array(Image.fromarray((fibre * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.8)).resize((size, size))) / 255.
    fibre = np.repeat(fibre[::6], 6, axis=0)[:size]  # stretch along the grain
    tone = .5 + (grain - grain.mean()) * 1.25 + (fibre - .5) * .10
    light = np.array([.925, .745, .455])
    dark = np.array([.800, .585, .300])
    colour = dark + (light - dark) * np.clip(tone, 0, 1)[..., None]
    shade = 1.045 - .11 * ((x / size) * .45 + (y / size) * .55)  # brighter towards the upper left
    return colour * shade[..., None]


def stone(player, size=384):
    """A lens-shaped stone with a baked contact shadow towards the lower right."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    cx, cy, radius = size * .5, size * .5, size * .44
    dx, dy = (x - cx) / radius, (y - cy) / radius
    dist = np.sqrt(dx * dx + dy * dy)
    inside = np.clip((1 - dist) * radius / 1.4, 0, 1)  # anti-aliased edge
    nz = np.sqrt(np.clip(1 - np.minimum(dist, 1) ** 2, 0, 1))
    nz = .35 + .65 * nz  # flatter than a sphere, like a real stone
    norm = np.sqrt(dx * dx + dy * dy + nz * nz)
    nx, ny, nz = dx / norm, dy / norm, nz / norm
    lx, ly, lz = -.46, -.56, .69
    diffuse = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
    hx, hy, hz = lx, ly, lz + 1
    hn = np.sqrt(hx * hx + hy * hy + hz * hz)
    specular = np.clip((nx * hx + ny * hy + nz * hz) / hn, 0, 1)
    rim = np.clip(dist, 0, 1) ** 6
    if player == 'B':
        value = .045 + .20 * diffuse ** 1.5 + .50 * specular ** 46 + .10 * specular ** 8 + .05 * rim
        rgb = np.stack([value * .96, value * .98, value * 1.04], -1)
    else:
        value = .70 + .29 * diffuse ** .75 + .10 * specular ** 30 - .10 * rim
        rgb = np.stack([value * 1.00, value * .992, value * .965], -1)
    sx, sy = cx + size * .030, cy + size * .040
    shadow_dist = np.sqrt((x - sx) ** 2 + (y - sy) ** 2) / (radius * 1.035)
    shadow = np.clip(1.13 - shadow_dist, 0, 1) ** 1.4 * .80
    shadow = np.array(Image.fromarray((np.clip(shadow, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(size * .022))) / 255.
    alpha = inside + (1 - inside) * shadow
    colour = rgb * inside[..., None] / np.maximum(alpha, 1e-6)[..., None]
    return np.concatenate([colour, alpha[..., None]], -1)


SHADOW_BORDER = 40  # px; plugins/katrain/skin.py stretches the texture with this border


def soft_shadow(size=128, border=SHADOW_BORDER):
    """A blurred rounded square used as a nine-patch for every drop shadow.

    Alpha is zero at the outer edge and full `border` px inside it, so drawing
    the patch that much larger than a surface puts the whole falloff outside it.
    Stretching a small texture costs almost nothing per frame, unlike a blur shader.
    """
    from PIL import ImageDraw
    image = Image.new('L', (size, size), 0)
    inset = border // 2
    ImageDraw.Draw(image).rounded_rectangle((inset, inset, size - 1 - inset, size - 1 - inset), radius=10, fill=255)
    alpha = np.array(image.filter(ImageFilter.GaussianBlur(border / 5.2))) / 255.
    return np.concatenate([np.zeros((size, size, 3)), alpha[..., None]], -1)


if __name__ == '__main__':
    save('kx_board.png', board())
    save('kx_stone_b.png', stone('B'))
    save('kx_stone_w.png', stone('W'))
    save('kx_shadow.png', soft_shadow())
