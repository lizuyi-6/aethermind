import hashlib
import math
import struct
from array import array


def _iter_char_ngrams(text: str, n: int = 3):
    compact = "".join(ch for ch in text if not ch.isspace())
    if not compact:
        return
    if len(compact) < n:
        yield compact
        return
    for i in range(0, len(compact) - n + 1):
        yield compact[i : i + n]


def text_to_vector(text: str, dim: int = 2048) -> list[float]:
    vec = [0.0] * dim
    for gram in _iter_char_ngrams(text, n=3):
        digest = hashlib.sha256(gram.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0) * 0.25
        vec[idx] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        inv = 1.0 / norm
        vec = [v * inv for v in vec]
    return vec


def vector_to_blob(vec: list[float], dtype: str = "float16") -> bytes:
    if dtype == "float32":
        arr = array("f", vec)
        return arr.tobytes()
    if dtype == "float16":
        fmt = "<" + ("e" * len(vec))
        return struct.pack(fmt, *vec)
    raise ValueError(f"unsupported vector dtype: {dtype}")


def blob_to_vector(blob: bytes, dtype: str = "float16") -> list[float]:
    if dtype == "float32":
        arr = array("f")
        arr.frombytes(blob)
        return arr.tolist()
    if dtype == "float16":
        count = len(blob) // 2
        return list(struct.unpack("<" + ("e" * count), blob))
    raise ValueError(f"unsupported vector dtype: {dtype}")


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
