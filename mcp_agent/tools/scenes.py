"""
Layers & Scenes MCP tools for Tu SketchUp Agent.
"""

import json
from typing import Optional, Union, Dict, Any
from mcp.server.fastmcp import FastMCP
from ..transport import send_to_sketchup
from .common import build_ids_payload, add_model_state_guard


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def sketchup_get_layers(name_filter: Optional[str] = None) -> str:
        payload: Dict[str, Any] = {}
        if name_filter:
            payload["name_filter"] = name_filter
        res = send_to_sketchup("get_layers", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_layer(
        name: str,
        color: Optional[Union[str, list[int]]] = None,
        visible: bool = True,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {"name": name, "visible": visible}
        if color is not None:
            payload["color"] = color
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("create_layer", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_entity_layer(
        layer_name: str,
        persistent_ids: Optional[list[Union[int, str]]] = None,
        entity_ids: Optional[list[Union[int, str]]] = None,
        ids: Optional[list[Union[int, str]]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        payload = build_ids_payload(persistent_ids, entity_ids, ids)
        payload["layer_name"] = layer_name
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("set_entity_layer", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_layer_visibility(
        layer_name: Optional[str] = None,
        visible: bool = True,
        layers: Optional[Dict[str, bool]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {}
        if layers is not None:
            payload["layers"] = layers
        elif layer_name is not None:
            payload["layer_name"] = layer_name
            payload["visible"] = visible
        else:
            raise ValueError("Cần cung cấp layer_name hoặc dictionary layers")
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("set_layer_visibility", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_get_scenes(name_filter: Optional[str] = None) -> str:
        payload: Dict[str, Any] = {}
        if name_filter:
            payload["name_filter"] = name_filter
        res = send_to_sketchup("get_scenes", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_create_scene(
        name: str,
        preset: Optional[str] = None,
        camera: Optional[Dict[str, Any]] = None,
        perspective: bool = False,
        hidden_layers: Optional[list[str]] = None,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {"name": name, "perspective": perspective}
        if preset:
            payload["preset"] = preset
        if camera:
            payload["camera"] = camera
        if hidden_layers:
            payload["hidden_layers"] = hidden_layers
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("create_scene", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_activate_scene(
        name: str,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        payload = {"name": name}
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("activate_scene", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    @mcp.tool()
    def sketchup_set_camera_view(
        preset: Optional[str] = None,
        perspective: bool = False,
        eye: Optional[list[float]] = None,
        target: Optional[list[float]] = None,
        up: Optional[list[float]] = None,
        zoom_extents: bool = True,
        expected_model_revision: Optional[int] = None,
        expected_model_session_id: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {"perspective": perspective, "zoom_extents": zoom_extents}
        if preset:
            payload["preset"] = preset
        if eye is not None:
            payload["eye"] = eye
        if target is not None:
            payload["target"] = target
        if up is not None:
            payload["up"] = up
        add_model_state_guard(payload, expected_model_revision, expected_model_session_id)
        res = send_to_sketchup("set_camera_view", payload)
        return json.dumps(res, indent=2, ensure_ascii=False)
