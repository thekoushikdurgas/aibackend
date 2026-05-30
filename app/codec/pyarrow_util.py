"""Optional PyArrow helpers (lazy import)."""

from __future__ import annotations

from typing import Any, Optional, Tuple

_pa_module: Optional[Any] = None
_pq_module: Optional[Any] = None
_ipc_module: Optional[Any] = None
_import_attempted = False


def try_import_pyarrow() -> Tuple[Optional[Any], Optional[Any]]:
    """Return (pyarrow, pyarrow.parquet) modules or (None, None)."""
    global _pa_module, _pq_module, _import_attempted
    if _import_attempted:
        return _pa_module, _pq_module
    _import_attempted = True
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        _pa_module = pa
        _pq_module = pq
    except ImportError:
        _pa_module = None
        _pq_module = None
    return _pa_module, _pq_module


def try_import_pyarrow_ipc(pa_module: Any) -> Optional[Any]:
    """Return pyarrow.ipc module when pyarrow is available."""
    global _ipc_module
    if _ipc_module is not None:
        return _ipc_module
    if pa_module is None:
        return None
    try:
        import pyarrow.ipc as ipc

        _ipc_module = ipc
        return ipc
    except ImportError:
        return None
