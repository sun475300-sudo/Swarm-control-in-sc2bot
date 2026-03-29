# -*- coding: utf-8 -*-
"""Optional OpenCL acceleration bridge with safe CPU fallback.

This module is intentionally dependency-tolerant:
- If `pyopencl` is available, it computes nearest-point index on OpenCL device.
- Otherwise it falls back to a pure Python implementation.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple


try:
    import pyopencl as cl
    import numpy as np
except Exception:
    cl = None
    np = None


_OPENCL_CTX = None
_OPENCL_QUEUE = None
_OPENCL_PRG = None


def _ensure_opencl():
    """Lazily initialize OpenCL context/program once."""
    global _OPENCL_CTX, _OPENCL_QUEUE, _OPENCL_PRG

    if cl is None or np is None:
        return False
    if _OPENCL_CTX is not None and _OPENCL_QUEUE is not None and _OPENCL_PRG is not None:
        return True

    try:
        _OPENCL_CTX = cl.create_some_context(interactive=False)
        _OPENCL_QUEUE = cl.CommandQueue(_OPENCL_CTX)
        _OPENCL_PRG = cl.Program(
            _OPENCL_CTX,
            """
            __kernel void dist_sq(
                const float ox,
                const float oy,
                __global const float2* points,
                __global float* out
            ) {
                int gid = get_global_id(0);
                float dx = ox - points[gid].x;
                float dy = oy - points[gid].y;
                out[gid] = dx * dx + dy * dy;
            }
            """,
        ).build()
        return True
    except Exception:
        _OPENCL_CTX = None
        _OPENCL_QUEUE = None
        _OPENCL_PRG = None
        return False


def nearest_point_index_opencl(
    origin: Tuple[float, float],
    points: Sequence[Tuple[float, float]],
) -> Optional[int]:
    """Return nearest point index, trying OpenCL first and CPU fallback."""
    if not points:
        return None

    ox, oy = float(origin[0]), float(origin[1])

    if _ensure_opencl():
        try:
            n = len(points)
            points_np = np.asarray(points, dtype=np.float32)
            out_np = np.empty((n,), dtype=np.float32)

            mf = cl.mem_flags
            points_buf = cl.Buffer(_OPENCL_CTX, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=points_np)
            out_buf = cl.Buffer(_OPENCL_CTX, mf.WRITE_ONLY, out_np.nbytes)

            _OPENCL_PRG.dist_sq(
                _OPENCL_QUEUE,
                (n,),
                None,
                np.float32(ox),
                np.float32(oy),
                points_buf,
                out_buf,
            )
            cl.enqueue_copy(_OPENCL_QUEUE, out_np, out_buf)
            _OPENCL_QUEUE.finish()

            return int(np.argmin(out_np))
        except Exception:
            pass

    best_idx = None
    best_dist_sq = float("inf")
    for i, (px, py) in enumerate(points):
        dx = ox - float(px)
        dy = oy - float(py)
        dist_sq = dx * dx + dy * dy
        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best_idx = i

    return best_idx
