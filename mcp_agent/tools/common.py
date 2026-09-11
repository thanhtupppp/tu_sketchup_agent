"""
Common helpers for MCP tools.
"""

from typing import Optional, Union, Dict, Any


def build_ids_payload(
    persistent_ids: Optional[Union[list[Union[int, str]], int, str]] = None,
    entity_ids: Optional[Union[list[Union[int, str]], int, str]] = None,
    ids: Optional[Union[list[Union[int, str]], int, str]] = None,
) -> Dict[str, Any]:
    if persistent_ids is not None:
        pids = persistent_ids if isinstance(persistent_ids, list) else [persistent_ids]
        return {"persistent_ids": pids}
    if entity_ids is not None:
        eids = entity_ids if isinstance(entity_ids, list) else [entity_ids]
        return {"entity_ids": eids}
    if ids is not None:
        id_list = ids if isinstance(ids, list) else [ids]
        return {"persistent_ids": id_list}
    raise ValueError("Cần cung cấp ít nhất một danh sách ID đối tượng: persistent_ids hoặc entity_ids")
