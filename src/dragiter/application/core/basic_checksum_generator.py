import hashlib
import json
from dataclasses import is_dataclass, fields
from typing import Any, Set, Dict, Union

from dragiter.domain.ports.checksum_generator import ChecksumGenerator


class BasicChecksumGenerator(ChecksumGenerator):

    def _to_canonical_dict(
            self,  # <-- ADDED self
            obj: Any,
            visited: Union[Set[int], None] = None,
            _memo: Union[Dict[int, Any], None] = None
    ) -> Any:
        """Optimized version with memoization and safe cycle detection."""
        if visited is None:
            visited = set()
        if _memo is None:
            _memo = {}

        obj_id = id(obj)

        if obj_id in _memo:
            return _memo[obj_id]

        if obj_id in visited:
            result = "<circular_reference>"
            _memo[obj_id] = result
            return result

        visited.add(obj_id)

        if is_dataclass(obj) and not isinstance(obj, type):
            result = {
                # FIX: Use self._to_canonical_dict instead of BasicChecksumGenerator._to_canonical_dict
                f.name: self._to_canonical_dict(getattr(obj, f.name), visited, _memo)
                for f in sorted(fields(obj), key=lambda x: x.name)
            }
        elif hasattr(obj, "__dict__") and not isinstance(obj, type):
            result = {
                k: self._to_canonical_dict(v, visited, _memo)
                for k, v in sorted(vars(obj).items())
            }
        elif isinstance(obj, dict):
            result = {
                k: self._to_canonical_dict(v, visited, _memo)
                for k, v in sorted(obj.items())
            }
        elif isinstance(obj, (list, tuple)):
            result = [self._to_canonical_dict(item, visited, _memo) for item in obj]
        elif isinstance(obj, (set, frozenset)):
            canonical_items = [self._to_canonical_dict(item, visited, _memo) for item in obj]
            result = sorted(canonical_items, key=lambda x: str(x))
        elif isinstance(obj, (str, int, float, bool, type(None))):
            result = obj
        else:
            result = str(obj)

        visited.remove(obj_id)
        _memo[obj_id] = result
        return result

    def compute_checksum(self, obj: Any) -> str:  # <-- ADDED self
        """Optimized checksum calculation"""

        # FIX: Call the internal method using self
        data = self._to_canonical_dict(obj)

        canonical_json = json.dumps(
            data,
            sort_keys=False,
            ensure_ascii=False,
            separators=(',', ':'),
            default=str
        )

        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()