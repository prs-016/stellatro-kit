"""Tint Stellatro card assets by remapping their PNG pixel palettes.

This script uses only the Python standard library. It rewrites PNG IDAT data
for 8-bit RGB/RGBA images and preserves the surrounding PNG chunks.
"""

from __future__ import annotations

import argparse
import binascii
import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

CLOVER_COLORS = {
    (48, 48, 48): (40, 120, 216),
    (84, 84, 84): (75, 149, 232),
    (120, 120, 120): (119, 180, 242),
    (161, 161, 161): (168, 210, 250),
    (186, 186, 186): (197, 226, 252),
    (212, 212, 212): (216, 236, 255),
}

DIAMOND_COLORS = {
    (186, 20, 29): (204, 89, 18),
    (153, 0, 48): (151, 58, 0),
}


class PngFormatError(ValueError):
    pass


def read_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(PNG_SIGNATURE):
        raise PngFormatError("Not a PNG file")

    chunks: list[tuple[bytes, bytes]] = []
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        if offset + 8 > len(data):
            raise PngFormatError("Truncated PNG chunk header")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + length
        chunk_end = chunk_data_end + 4
        if chunk_end > len(data):
            raise PngFormatError(f"Truncated {chunk_type.decode('latin1')} chunk")
        chunks.append((chunk_type, data[chunk_data_start:chunk_data_end]))
        offset = chunk_end
        if chunk_type == b"IEND":
            break
    return chunks


def write_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
    crc = binascii.crc32(chunk_type)
    crc = binascii.crc32(chunk_data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(chunk_data)) + chunk_type + chunk_data + struct.pack(">I", crc)


def paeth_predictor(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    distance_left = abs(estimate - left)
    distance_above = abs(estimate - above)
    distance_upper_left = abs(estimate - upper_left)
    if distance_left <= distance_above and distance_left <= distance_upper_left:
        return left
    if distance_above <= distance_upper_left:
        return above
    return upper_left


def unfilter_scanlines(raw: bytes, width: int, height: int, bytes_per_pixel: int) -> bytearray:
    row_length = width * bytes_per_pixel
    expected_length = height * (row_length + 1)
    if len(raw) != expected_length:
        raise PngFormatError(f"Unexpected decompressed image data length: {len(raw)}")

    pixels = bytearray(height * row_length)
    raw_offset = 0
    pixel_offset = 0
    previous_row = bytearray(row_length)

    for _ in range(height):
        filter_type = raw[raw_offset]
        raw_offset += 1
        scanline = bytearray(raw[raw_offset : raw_offset + row_length])
        raw_offset += row_length

        for i, value in enumerate(scanline):
            left = scanline[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
            above = previous_row[i]
            upper_left = previous_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0

            if filter_type == 0:
                reconstructed = value
            elif filter_type == 1:
                reconstructed = value + left
            elif filter_type == 2:
                reconstructed = value + above
            elif filter_type == 3:
                reconstructed = value + ((left + above) // 2)
            elif filter_type == 4:
                reconstructed = value + paeth_predictor(left, above, upper_left)
            else:
                raise PngFormatError(f"Unsupported PNG filter type: {filter_type}")

            scanline[i] = reconstructed & 0xFF

        pixels[pixel_offset : pixel_offset + row_length] = scanline
        pixel_offset += row_length
        previous_row = scanline

    return pixels


def filter_scanlines_none(pixels: bytes, width: int, height: int, bytes_per_pixel: int) -> bytes:
    row_length = width * bytes_per_pixel
    filtered = bytearray()
    for y in range(height):
        row_start = y * row_length
        filtered.append(0)
        filtered.extend(pixels[row_start : row_start + row_length])
    return bytes(filtered)


def diamond_tint(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    if rgb in DIAMOND_COLORS:
        return DIAMOND_COLORS[rgb]

    red, green, blue = rgb
    if 230 <= red <= 245 and 20 <= green <= 35 and 29 <= blue <= 42:
        return (245, 122, 31)
    return rgb


def tint_pixels(pixels: bytearray, color_type: int, suit: str) -> int:
    bytes_per_pixel = 4 if color_type == 6 else 3
    changed = 0

    for offset in range(0, len(pixels), bytes_per_pixel):
        red = pixels[offset]
        green = pixels[offset + 1]
        blue = pixels[offset + 2]
        rgb = (red, green, blue)

        if suit == "clovers":
            new_rgb = CLOVER_COLORS.get(rgb, rgb)
        elif suit == "diamonds":
            new_rgb = diamond_tint(rgb)
        else:
            new_rgb = rgb

        if new_rgb != rgb:
            pixels[offset] = new_rgb[0]
            pixels[offset + 1] = new_rgb[1]
            pixels[offset + 2] = new_rgb[2]
            changed += 1

    return changed


def tint_png(path: Path, suit: str, dry_run: bool) -> int:
    chunks = read_chunks(path.read_bytes())
    ihdr = next((chunk_data for chunk_type, chunk_data in chunks if chunk_type == b"IHDR"), None)
    if ihdr is None:
        raise PngFormatError("PNG is missing IHDR")

    width, height, bit_depth, color_type, compression, png_filter, interlace = struct.unpack(">IIBBBBB", ihdr)
    if bit_depth != 8 or color_type not in {2, 6} or compression != 0 or png_filter != 0 or interlace != 0:
        raise PngFormatError(
            f"Unsupported PNG format in {path}: bit_depth={bit_depth}, "
            f"color_type={color_type}, interlace={interlace}"
        )

    bytes_per_pixel = 4 if color_type == 6 else 3
    idat_data = b"".join(chunk_data for chunk_type, chunk_data in chunks if chunk_type == b"IDAT")
    pixels = unfilter_scanlines(zlib.decompress(idat_data), width, height, bytes_per_pixel)
    changed = tint_pixels(pixels, color_type, suit)

    if dry_run or changed == 0:
        return changed

    new_idat = zlib.compress(filter_scanlines_none(pixels, width, height, bytes_per_pixel), level=9)
    output = bytearray(PNG_SIGNATURE)
    wrote_idat = False

    for chunk_type, chunk_data in chunks:
        if chunk_type == b"IDAT":
            if not wrote_idat:
                output.extend(write_chunk(b"IDAT", new_idat))
                wrote_idat = True
            continue
        output.extend(write_chunk(chunk_type, chunk_data))

    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(output)
    temp_path.replace(path)
    return changed


def tint_suit(cards_root: Path, suit: str, dry_run: bool) -> tuple[int, int]:
    suit_dir = cards_root / suit
    if not suit_dir.is_dir():
        raise FileNotFoundError(f"Missing suit folder: {suit_dir}")

    files_changed = 0
    pixels_changed = 0
    for path in sorted(suit_dir.glob("*.png")):
        changed = tint_png(path, suit, dry_run)
        if changed:
            files_changed += 1
            pixels_changed += changed
            action = "would tint" if dry_run else "tinted"
            print(f"{action}: {path} ({changed} pixels)")
    return files_changed, pixels_changed


def default_cards_root() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "stellatro_cards"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tint Stellatro clovers blue and diamonds orange.")
    parser.add_argument(
        "--cards-root",
        type=Path,
        default=default_cards_root(),
        help="Path to the stellatro_cards folder.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without rewriting PNGs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cards_root = args.cards_root.resolve()
    total_files = 0
    total_pixels = 0

    for suit in ("clovers", "diamonds"):
        files, pixels = tint_suit(cards_root, suit, args.dry_run)
        total_files += files
        total_pixels += pixels

    action = "Would tint" if args.dry_run else "Tinted"
    print(f"{action} {total_files} files and {total_pixels} pixels under {cards_root}")


if __name__ == "__main__":
    main()
