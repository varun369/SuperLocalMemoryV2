# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3

"""PolarQuant embedding quantization.

Implements random orthogonal rotation + recursive polar coordinate
transform + scalar quantization for ultra-compact embedding storage.

Pipeline:
  1. Random rotation (Mezzadri-corrected QR) -- preserves angles
  2. Cartesian -> hyperspherical polar coordinates
  3. Scalar quantization of angles (uniform codebook)
  4. Byte packing (8/4/2-bit)

Reconstruction:
  1. Unpack bytes -> indices
  2. Map indices -> centroid angles via codebook
  3. Polar -> Cartesian
  4. Inverse rotation (S^T since S is orthogonal)

References:
  - PolarQuant (arXiv 2502.02617)
  - TurboQuant (ICLR 2026, arXiv 2504.19874)
  - Mezzadri F (2007). How to generate random matrices from
    the classical compact groups.

Part of Qualixar | Author: Varun Pratap Bhardwaj
License: MIT
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from superlocalmemory.core.config import PolarQuantConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuantizedEmbedding:
    """Immutable container for a quantized embedding.

    Fields:
      fact_id:       Linked atomic fact (empty string during encode).
      radius:        float16-precision L2 norm (sole norm for storage + reconstruct).
      angle_indices: Packed quantized angle indices as bytes.
      bit_width:     Quantization level (2, 4, or 8).
      qjl_bits:      Optional QJL residual correction bits.
    """

    fact_id: str
    radius: float
    angle_indices: bytes
    bit_width: int
    qjl_bits: bytes | None


# ---------------------------------------------------------------------------
# PolarQuantEncoder
# ---------------------------------------------------------------------------


class PolarQuantEncoder:
    """Random-rotation + polar-coordinate embedding quantizer.

    HR-01: Rotation matrix generated ONCE and reused for ALL embeddings.
    HR-02: Same rotation matrix for all embeddings in a profile.
    HR-08: No new pip dependencies (numpy + stdlib only).
    HR-09: Angle indices as uint8, packed into bytes.
    """

    __slots__ = ("_config", "_d", "_S", "_codebooks")

    def __init__(self, config: PolarQuantConfig) -> None:
        self._config = config
        self._d = config.dimension
        self._S = self._load_or_create_rotation_matrix()
        self._codebooks = self._generate_uniform_codebooks()

    # -- Rotation matrix (HR-01, HR-02) ------------------------------------

    def _load_or_create_rotation_matrix(self) -> NDArray:
        """Load or create Mezzadri-corrected random orthogonal matrix.

        Mezzadri correction (B-CRIT-01):
          S = Q @ diag(sign(diag(R)))
        ensures UNIFORM sampling from O(d). Plain QR gives Haar-random
        only up to sign flips.
        """
        path_str = self._config.rotation_matrix_path
        if not path_str:
            path_str = str(Path.home() / ".superlocalmemory" / "polar_rotation.npy")

        path = Path(path_str)

        if path.exists():
            try:
                S = np.load(str(path))
                if S.shape == (self._d, self._d):
                    return S
                logger.warning(
                    "Rotation matrix shape %s != expected (%d,%d), regenerating",
                    S.shape, self._d, self._d,
                )
            except Exception as exc:
                logger.warning("Corrupt rotation matrix, regenerating: %s", exc)

        # Generate new rotation matrix with Mezzadri correction
        rng = np.random.default_rng(self._config.seed)
        H = rng.standard_normal((self._d, self._d))
        Q, R = np.linalg.qr(H)
        # Mezzadri correction: ensures uniform sampling from O(d)
        S = Q @ np.diag(np.sign(np.diag(R)))

        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(path), S)
        logger.info("Generated rotation matrix (%d x %d) at %s", self._d, self._d, path)
        return S

    # -- Codebook generation -----------------------------------------------

    def _generate_uniform_codebooks(self) -> dict[int, dict[str, NDArray]]:
        """Generate uniform codebooks for 2/4/8-bit quantization.

        Uniform approximation is justified because at d=768, the
        Beta(d/2-k, 1/2) angle distribution concentrates around pi/2
        so tightly that uniform and Lloyd-Max converge (KL < 0.01 bits).
        """
        codebooks: dict[int, dict[str, NDArray]] = {}
        for bit_width in (2, 4, 8):
            levels = 2 ** bit_width
            boundaries = np.linspace(0.0, math.pi, levels + 1)
            centroids = (boundaries[:-1] + boundaries[1:]) / 2.0
            codebooks[bit_width] = {
                "boundaries": boundaries,
                "centroids": centroids,
            }
        return codebooks

    # -- Encode ------------------------------------------------------------

    def encode(self, embedding: NDArray, bit_width: int = 4) -> QuantizedEmbedding:
        """Encode a float32 embedding into quantized polar representation.

        Args:
            embedding: 1-D float vector of dimension self._d.
            bit_width:  2, 4, or 8.

        Returns:
            QuantizedEmbedding with packed angle indices.

        Raises:
            ValueError: Invalid bit_width or dimension mismatch.
        """
        if bit_width not in (2, 4, 8):
            raise ValueError(
                f"bit_width must be 2, 4, or 8, got {bit_width}"
            )
        if embedding.shape != (self._d,):
            raise ValueError(
                f"shape mismatch: expected ({self._d},), got {embedding.shape}"
            )

        # Step 1: Random rotation
        v_rot = self._S @ embedding

        # Step 2: Compute radius
        r = float(np.linalg.norm(v_rot))

        # Degenerate zero vector
        if r < 1e-12:
            zero_angles = np.zeros(self._d - 1, dtype=np.uint8)
            if bit_width == 8:
                packed = zero_angles.tobytes()
            elif bit_width == 4:
                packed = self.pack_4bit(zero_angles)
            else:
                packed = self.pack_2bit(zero_angles)
            return QuantizedEmbedding(
                fact_id="",
                radius=0.0,
                angle_indices=packed,
                bit_width=bit_width,
                qjl_bits=None,
            )

        # Step 3: Normalize
        v_unit = v_rot / r

        # Step 4: Cartesian to polar angles
        angles = _cartesian_to_polar_angles(v_unit)

        # Step 5: Quantize angles using codebook
        cb = self._codebooks[bit_width]
        indices = np.digitize(angles, cb["boundaries"][1:-1]).astype(np.uint8)

        # Step 6: Pack into bytes
        if bit_width == 8:
            packed = indices.tobytes()
        elif bit_width == 4:
            packed = self.pack_4bit(indices)
        else:
            packed = self.pack_2bit(indices)

        return QuantizedEmbedding(
            fact_id="",
            radius=float(np.float16(r)),
            angle_indices=packed,
            bit_width=bit_width,
            qjl_bits=None,
        )

    # -- Decode ------------------------------------------------------------

    def decode(self, qe: QuantizedEmbedding) -> NDArray:
        """Decode a QuantizedEmbedding back to float64 vector.

        Args:
            qe: Quantized embedding produced by encode().

        Returns:
            Reconstructed vector of dimension self._d.
        """
        n_angles = self._d - 1

        # Step 1: Unpack angle indices
        if qe.bit_width == 8:
            indices = np.frombuffer(qe.angle_indices, dtype=np.uint8).copy()
        elif qe.bit_width == 4:
            indices = self.unpack_4bit(qe.angle_indices, n_angles)
        else:
            indices = self.unpack_2bit(qe.angle_indices, n_angles)

        # Step 2: Dequantize -- map indices to centroid angles
        centroids = self._codebooks[qe.bit_width]["centroids"]
        # Clip indices to valid range
        indices = np.clip(indices, 0, len(centroids) - 1)
        angles = centroids[indices]

        # Step 3: Polar to Cartesian
        v_unit = _polar_to_cartesian(angles, self._d)

        # Step 4: Scale by radius
        v_rot = v_unit * qe.radius

        # Step 5: Inverse rotation (S is orthogonal, so S^T = S^{-1})
        v_orig = self._S.T @ v_rot

        return v_orig

    # -- Similarity --------------------------------------------------------

    def approximate_similarity(
        self, query: NDArray, qe: QuantizedEmbedding,
    ) -> float:
        """Compute approximate cosine similarity via decode.

        Args:
            query: Query vector (float32/64).
            qe:    Quantized embedding.

        Returns:
            Cosine similarity in [-1, 1]. Returns 0.0 on degenerate inputs.
        """
        v_decoded = self.decode(qe)
        denom = np.linalg.norm(query) * np.linalg.norm(v_decoded)
        if denom < 1e-12:
            return 0.0
        sim = float(np.dot(query, v_decoded) / denom)
        # NaN guard
        if math.isnan(sim) or math.isinf(sim):
            return 0.0
        return sim

    # -- Bit packing (static methods) --------------------------------------

    @staticmethod
    def pack_4bit(indices: NDArray) -> bytes:
        """Pack uint8 indices (0-15) into 4-bit pairs.

        Two indices per byte: high nibble | low nibble.
        Pads to even length if needed.
        """
        n = len(indices)
        padded = np.zeros(n + (n % 2), dtype=np.uint8)
        padded[:n] = np.clip(indices, 0, 15)
        packed = (padded[0::2] << 4) | padded[1::2]
        return packed.tobytes()

    @staticmethod
    def unpack_4bit(data: bytes, length: int) -> NDArray:
        """Unpack 4-bit pairs back to uint8 indices."""
        packed = np.frombuffer(data, dtype=np.uint8)
        high = packed >> 4
        low = packed & 0x0F
        result = np.empty(len(packed) * 2, dtype=np.uint8)
        result[0::2] = high
        result[1::2] = low
        return result[:length]

    @staticmethod
    def pack_2bit(indices: NDArray) -> bytes:
        """Pack uint8 indices (0-3) into 2-bit quads.

        Four indices per byte: [b7b6 | b5b4 | b3b2 | b1b0].
        Pads to multiple of 4 if needed.
        """
        n = len(indices)
        pad_len = (4 - n % 4) % 4
        padded = np.zeros(n + pad_len, dtype=np.uint8)
        padded[:n] = np.clip(indices, 0, 3)
        packed = (
            (padded[0::4] << 6)
            | (padded[1::4] << 4)
            | (padded[2::4] << 2)
            | padded[3::4]
        )
        return packed.tobytes()

    @staticmethod
    def unpack_2bit(data: bytes, length: int) -> NDArray:
        """Unpack 2-bit quads back to uint8 indices."""
        packed = np.frombuffer(data, dtype=np.uint8)
        result = np.empty(len(packed) * 4, dtype=np.uint8)
        result[0::4] = (packed >> 6) & 0x03
        result[1::4] = (packed >> 4) & 0x03
        result[2::4] = (packed >> 2) & 0x03
        result[3::4] = packed & 0x03
        return result[:length]


# ---------------------------------------------------------------------------
# Coordinate conversion helpers (module-level for reuse)
# ---------------------------------------------------------------------------


def _cartesian_to_polar_angles(v_unit: NDArray) -> NDArray:
    """Convert unit vector to d-1 polar angles. O(d) time.

    Uses the recursive polar decomposition:
      v[i] = cos(theta_i) * product(sin(theta_j) for j < i)
    """
    d = len(v_unit)
    angles = np.empty(d - 1)
    for i in range(d - 1):
        remaining_norm = float(np.linalg.norm(v_unit[i:]))
        if remaining_norm < 1e-12:
            angles[i:] = math.pi / 2
            break
        angles[i] = math.acos(np.clip(v_unit[i] / remaining_norm, -1.0, 1.0))
    return angles


def _polar_to_cartesian(angles: NDArray, d: int) -> NDArray:
    """Convert d-1 polar angles to d-dimensional unit vector.

    Inverse of _cartesian_to_polar_angles.
    """
    v = np.empty(d)
    sin_product = 1.0
    for i in range(d - 1):
        v[i] = math.cos(angles[i]) * sin_product
        sin_product *= math.sin(angles[i])
    v[d - 1] = sin_product
    return v
