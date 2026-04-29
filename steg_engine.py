"""
Universal LSB Steganography Engine  –  NumPy-accelerated edition
Encodes ANY file into a PNG image using Least Significant Bit technique.

Speed improvement vs. the old pure-Python loop engine:
  • Old: iterate every pixel in Python  →  ~10-60 s for a large image
  • New: vectorised NumPy bit-ops        →  < 1 s for the same image
"""

import struct
import io
import numpy as np
from PIL import Image

MAGIC   = b'STEGX'   # 5-byte magic header
VERSION = 1


# ─────────────────────────────────────────────────────────────────────────────
# Core helpers  (NumPy-based, no Python loops over pixels)
# ─────────────────────────────────────────────────────────────────────────────

def _payload_to_bits(data: bytes) -> np.ndarray:
    """
    Convert a bytes object to a uint8 NumPy array of 0/1 bits (MSB first).
    e.g. 0b10110010  →  [1,0,1,1,0,0,1,0]
    """
    arr = np.frombuffer(data, dtype=np.uint8)
    # unpackbits gives MSB-first bits for each byte
    return np.unpackbits(arr)           # shape: (len(data)*8,)


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    """Convert a 0/1 uint8 NumPy array back to bytes."""
    # pad to multiple of 8
    pad = (-len(bits)) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    return np.packbits(bits).tobytes()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def capacity(img: Image.Image) -> int:
    """Return max bytes we can hide in this image (1 LSB per RGB channel)."""
    w, h = img.size
    total_bits = w * h * 3          # R, G, B each hold 1 LSB
    return (total_bits // 8) - 64  # reserve 64 bytes for header overhead


def encode(cover_image_bytes: bytes, secret_bytes: bytes, filename: str) -> bytes:
    """
    Hide secret_bytes (with filename metadata) inside a PNG cover image.
    Returns PNG bytes of the steg image.
    """
    img = Image.open(io.BytesIO(cover_image_bytes)).convert('RGB')

    # ── Build header ──────────────────────────────────────────────────────────
    # [MAGIC 5b][VERSION 1b][filename_len 2b][filename Nb][payload_len 4b]
    fname_encoded = filename.encode('utf-8')[:255]
    header = (
        MAGIC
        + struct.pack('B', VERSION)
        + struct.pack('>H', len(fname_encoded))
        + fname_encoded
        + struct.pack('>I', len(secret_bytes))
    )
    full_payload = header + secret_bytes

    cap = capacity(img)
    if len(full_payload) > cap:
        raise ValueError(
            f"File too large! Max capacity: {cap:,} bytes, "
            f"your payload: {len(full_payload):,} bytes. "
            f"Use a larger cover image."
        )

    # ── Vectorised LSB embedding ──────────────────────────────────────────────
    # Image → flat uint8 array  shape: (H*W*3,)
    img_arr = np.array(img, dtype=np.uint8).flatten()

    # Payload → bit array  shape: (len(full_payload)*8,)
    bits = _payload_to_bits(full_payload)           # 0/1 values

    n_bits = len(bits)

    # Clear the LSB of the first n_bits channels, then OR in the payload bits
    img_arr[:n_bits] = (img_arr[:n_bits] & 0xFE) | bits

    # ── Reconstruct image ─────────────────────────────────────────────────────
    out_arr = img_arr.reshape((img.height, img.width, 3))
    out_img = Image.fromarray(out_arr, 'RGB')

    out_buf = io.BytesIO()
    out_img.save(out_buf, format='PNG', compress_level=1)
    return out_buf.getvalue()


def decode(steg_image_bytes: bytes) -> tuple:
    """
    Extract hidden file from a steg PNG.
    Returns (original_filename, file_bytes).
    Raises ValueError if no valid payload found.
    """
    img = Image.open(io.BytesIO(steg_image_bytes)).convert('RGB')

    # ── Extract LSBs in one shot ──────────────────────────────────────────────
    img_arr = np.array(img, dtype=np.uint8).flatten()
    lsbs = (img_arr & 1).astype(np.uint8)           # shape: (H*W*3,)

    # Helper: read N bytes from the bit stream starting at bit offset `pos`
    def read_bytes(pos: int, n_bytes: int) -> tuple:
        end = pos + n_bytes * 8
        return _bits_to_bytes(lsbs[pos:end]), end

    # ── Parse header ─────────────────────────────────────────────────────────
    header_bits = (len(MAGIC) + 1 + 2) * 8         # MAGIC + VERSION + fname_len
    if len(lsbs) < header_bits:
        raise ValueError("Image too small to contain a valid payload.")

    header_bytes, pos = read_bytes(0, len(MAGIC) + 1 + 2)

    if header_bytes[:5] != MAGIC:
        raise ValueError("No hidden file found in this image (magic bytes missing).")

    fname_len = struct.unpack('>H', header_bytes[6:8])[0]

    # ── Read filename ─────────────────────────────────────────────────────────
    fname_bytes, pos = read_bytes(pos, fname_len)
    try:
        filename = fname_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError("Corrupted payload: couldn't decode filename.")

    # ── Read payload length ───────────────────────────────────────────────────
    len_bytes, pos = read_bytes(pos, 4)
    payload_len = struct.unpack('>I', len_bytes)[0]

    # ── Read payload ──────────────────────────────────────────────────────────
    end_bit = pos + payload_len * 8
    if end_bit > len(lsbs):
        raise ValueError("Corrupted payload: file data truncated.")

    secret_bytes = _bits_to_bytes(lsbs[pos:end_bit])
    return filename, secret_bytes


def image_capacity_info(cover_image_bytes: bytes) -> dict:
    """Return capacity stats for a given cover image."""
    img = Image.open(io.BytesIO(cover_image_bytes)).convert('RGB')
    w, h = img.size
    cap = capacity(img)
    return {
        'width':    w,
        'height':   h,
        'pixels':   w * h,
        'max_bytes': cap,
        'max_kb':   round(cap / 1024, 1),
        'max_mb':   round(cap / (1024 * 1024), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import time

    test_img = Image.new('RGB', (1920, 1080), color=(128, 200, 100))
    buf = io.BytesIO()
    test_img.save(buf, 'PNG')
    cover = buf.getvalue()

    secret = b"Hello World! Speed test for NumPy steg engine." * 500

    t0  = time.perf_counter()
    steg_out = encode(cover, secret, "speedtest.txt")
    t1  = time.perf_counter()
    fname, recovered = decode(steg_out)
    t2  = time.perf_counter()

    assert fname    == "speedtest.txt"
    assert recovered == secret
    print(f"✅ Self-test PASSED")
    print(f"   encode: {t1-t0:.3f}s   decode: {t2-t1:.3f}s  "
          f"(image: 1920×1080, payload: {len(secret):,} bytes)")
    print(f"   Capacity: {image_capacity_info(cover)['max_mb']} MB")
