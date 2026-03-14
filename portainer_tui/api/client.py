"""Async Portainer REST API client."""

from __future__ import annotations

import json
from typing import Any

import httpx

from portainer_tui.config import InstanceConfig
from portainer_tui.models.container import Container
from portainer_tui.models.endpoint import Endpoint
from portainer_tui.models.image import Image
from portainer_tui.models.network import Network
from portainer_tui.models.stack import Stack
from portainer_tui.models.volume import Volume


class PortainerAPIError(Exception):
    """Raised when the Portainer API returns an error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PortainerClient:
    """Async HTTP client for the Portainer REST API (v2).

    Uses a fresh httpx.AsyncClient per request to avoid connection-pool
    race conditions when multiple Textual workers fire concurrently.
    The JWT token is cached after the first authentication call.
    """

    def __init__(self, instance: InstanceConfig) -> None:
        self._instance = instance
        self._base_url = instance.url.rstrip("/") + "/api"
        self._token: str | None = instance.token

    def _new_http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            verify=not self._instance.tls_skip_verify,
            timeout=30.0,
        )

    async def connect(self) -> None:
        """Authenticate if needed (no-op when using an API token)."""
        if not self._token:
            await self._authenticate()

    async def aclose(self) -> None:
        """No-op — connections are closed after each request."""

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _authenticate(self) -> None:
        async with self._new_http() as http:
            resp = await http.post(
                "/auth",
                headers={"Content-Type": "application/json"},
                json={
                    "username": self._instance.username,
                    "password": self._instance.password,
                },
            )
        data = self._handle(resp)
        self._token = data["jwt"]

    # ------------------------------------------------------------------
    # Endpoints / Environments
    # ------------------------------------------------------------------

    async def list_endpoints(self) -> list[Endpoint]:
        data = await self._get("/endpoints")
        return [Endpoint.from_api(e) for e in data]

    async def get_endpoint(self, endpoint_id: int) -> Endpoint:
        data = await self._get(f"/endpoints/{endpoint_id}")
        return Endpoint.from_api(data)

    # ------------------------------------------------------------------
    # Containers
    # ------------------------------------------------------------------

    async def list_containers(
        self, endpoint_id: int, all_containers: bool = True
    ) -> list[Container]:
        params: dict[str, Any] = {"all": 1 if all_containers else 0}
        data = await self._get(
            f"/endpoints/{endpoint_id}/docker/containers/json", params=params
        )
        return [Container.from_api(c) for c in data]

    async def inspect_container(self, endpoint_id: int, container_id: str) -> dict:
        return await self._get(
            f"/endpoints/{endpoint_id}/docker/containers/{container_id}/json"
        )

    async def start_container(self, endpoint_id: int, container_id: str) -> None:
        await self._post(
            f"/endpoints/{endpoint_id}/docker/containers/{container_id}/start"
        )

    async def stop_container(self, endpoint_id: int, container_id: str) -> None:
        await self._post(
            f"/endpoints/{endpoint_id}/docker/containers/{container_id}/stop"
        )

    async def restart_container(self, endpoint_id: int, container_id: str) -> None:
        await self._post(
            f"/endpoints/{endpoint_id}/docker/containers/{container_id}/restart"
        )

    async def remove_container(
        self, endpoint_id: int, container_id: str, force: bool = False
    ) -> None:
        await self._delete(
            f"/endpoints/{endpoint_id}/docker/containers/{container_id}",
            params={"force": int(force)},
        )

    async def create_container(
        self,
        endpoint_id: int,
        name: str,
        config: dict,
    ) -> str:
        """Create a container and return its ID."""
        data = await self._post(
            f"/endpoints/{endpoint_id}/docker/containers/create",
            params={"name": name},
            json_body=config,
        )
        return data["Id"]

    async def list_networks_for_container(
        self, endpoint_id: int, container_id: str
    ) -> list[str]:
        """Return network names the container is connected to."""
        data = await self._get(
            f"/endpoints/{endpoint_id}/docker/containers/{container_id}/json"
        )
        nets = data.get("NetworkSettings", {}).get("Networks", {})
        return list(nets.keys())

    async def connect_network(
        self, endpoint_id: int, network_id: str, container_id: str
    ) -> None:
        await self._post(
            f"/endpoints/{endpoint_id}/docker/networks/{network_id}/connect",
            json_body={"Container": container_id},
        )

    async def disconnect_network(
        self, endpoint_id: int, network_id: str, container_id: str, force: bool = False
    ) -> None:
        await self._post(
            f"/endpoints/{endpoint_id}/docker/networks/{network_id}/disconnect",
            json_body={"Container": container_id, "Force": force},
        )

    async def pull_image(self, endpoint_id: int, image_ref: str) -> None:
        """Pull (or update) a Docker image on the endpoint.

        ``image_ref`` may be ``"nginx:latest"``, ``"nginx"``, or a full
        registry path.  The tag defaults to ``latest`` when omitted.
        """
        if ":" in image_ref and not image_ref.startswith("sha256:"):
            name, tag = image_ref.rsplit(":", 1)
        else:
            name, tag = image_ref, "latest"
        await self._post(
            f"/endpoints/{endpoint_id}/docker/images/create",
            params={"fromImage": name, "tag": tag},
        )

    async def get_container_logs(
        self,
        endpoint_id: int,
        container_id: str,
        tail: int = 200,
        timestamps: bool = True,
    ) -> str:
        params = {
            "stdout": 1,
            "stderr": 1,
            "tail": tail,
            "timestamps": int(timestamps),
        }
        return await self._get_text(
            f"/endpoints/{endpoint_id}/docker/containers/{container_id}/logs",
            params=params,
        )

    # ------------------------------------------------------------------
    # Stacks
    # ------------------------------------------------------------------

    async def list_stacks(self, endpoint_id: int | None = None) -> list[Stack]:
        params: dict[str, Any] = {}
        if endpoint_id is not None:
            params["filters"] = json.dumps({"EndpointID": endpoint_id})
        data = await self._get("/stacks", params=params)
        return [Stack.from_api(s) for s in (data or [])]

    async def get_stack(self, stack_id: int) -> Stack:
        data = await self._get(f"/stacks/{stack_id}")
        return Stack.from_api(data)

    async def get_stack_file(self, stack_id: int) -> str:
        data = await self._get(f"/stacks/{stack_id}/file")
        return data.get("StackFileContent", "")

    async def remove_stack(self, stack_id: int, endpoint_id: int) -> None:
        await self._delete(f"/stacks/{stack_id}", params={"endpointId": endpoint_id})

    async def redeploy_stack(
        self,
        stack_id: int,
        endpoint_id: int,
        pull_image: bool = True,
    ) -> None:
        """Re-deploy a stack, pulling latest images when *pull_image* is True."""
        raw = await self._get(f"/stacks/{stack_id}")
        file_content = await self.get_stack_file(stack_id)
        payload: dict[str, Any] = {
            "StackFileContent": file_content,
            "Env": raw.get("Env") or [],
            "Prune": False,
            "PullImage": pull_image,
        }
        await self._put(
            f"/stacks/{stack_id}",
            params={"endpointId": endpoint_id},
            json_body=payload,
        )

    async def update_stack(
        self,
        stack_id: int,
        endpoint_id: int,
        stack_file_content: str,
        env: list[dict] | None = None,
        prune: bool = False,
    ) -> Stack:
        payload: dict[str, Any] = {
            "StackFileContent": stack_file_content,
            "Env": env or [],
            "Prune": prune,
        }
        data = await self._put(
            f"/stacks/{stack_id}",
            params={"endpointId": endpoint_id},
            json_body=payload,
        )
        return Stack.from_api(data)

    # ------------------------------------------------------------------
    # Volumes
    # ------------------------------------------------------------------

    async def list_volumes(self, endpoint_id: int) -> list[Volume]:
        data = await self._get(f"/endpoints/{endpoint_id}/docker/volumes")
        return [Volume.from_api(v) for v in (data.get("Volumes") or [])]

    async def inspect_volume(self, endpoint_id: int, volume_name: str) -> dict:
        return await self._get(
            f"/endpoints/{endpoint_id}/docker/volumes/{volume_name}"
        )

    async def remove_volume(self, endpoint_id: int, volume_name: str) -> None:
        await self._delete(f"/endpoints/{endpoint_id}/docker/volumes/{volume_name}")

    # ------------------------------------------------------------------
    # Networks
    # ------------------------------------------------------------------

    async def list_networks(self, endpoint_id: int) -> list[Network]:
        data = await self._get(f"/endpoints/{endpoint_id}/docker/networks")
        return [Network.from_api(n) for n in data]

    async def inspect_network(self, endpoint_id: int, network_id: str) -> dict:
        return await self._get(
            f"/endpoints/{endpoint_id}/docker/networks/{network_id}"
        )

    async def remove_network(self, endpoint_id: int, network_id: str) -> None:
        await self._delete(f"/endpoints/{endpoint_id}/docker/networks/{network_id}")

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    async def list_images(self, endpoint_id: int) -> list[Image]:
        data = await self._get(
            f"/endpoints/{endpoint_id}/docker/images/json", params={"all": 0}
        )
        return [Image.from_api(img) for img in data]

    async def inspect_image(self, endpoint_id: int, image_id: str) -> dict:
        return await self._get(
            f"/endpoints/{endpoint_id}/docker/images/{image_id}/json"
        )

    async def remove_image(
        self, endpoint_id: int, image_id: str, force: bool = False
    ) -> None:
        await self._delete(
            f"/endpoints/{endpoint_id}/docker/images/{image_id}",
            params={"force": int(force)},
        )

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._instance.token:
            headers["X-API-Key"] = self._instance.token
        elif self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _get(self, path: str, params: dict | None = None) -> Any:
        try:
            async with self._new_http() as http:
                resp = await http.get(path, headers=self._auth_headers(), params=params)
        except httpx.TransportError as e:
            raise PortainerAPIError(str(e)) from e
        return self._handle(resp)

    async def _get_text(self, path: str, params: dict | None = None) -> str:
        try:
            async with self._new_http() as http:
                resp = await http.get(path, headers=self._auth_headers(), params=params)
        except httpx.TransportError as e:
            raise PortainerAPIError(str(e)) from e
        if resp.status_code >= 400:
            raise PortainerAPIError(resp.text, resp.status_code)
        return resp.text

    async def _post(
        self,
        path: str,
        params: dict | None = None,
        json_body: Any = None,
    ) -> Any:
        try:
            async with self._new_http() as http:
                resp = await http.post(
                    path, headers=self._auth_headers(), params=params, json=json_body
                )
        except httpx.TransportError as e:
            raise PortainerAPIError(str(e)) from e
        return self._handle(resp)

    async def _put(
        self, path: str, params: dict | None = None, json_body: Any = None
    ) -> Any:
        try:
            async with self._new_http() as http:
                resp = await http.put(
                    path, headers=self._auth_headers(), params=params, json=json_body
                )
        except httpx.TransportError as e:
            raise PortainerAPIError(str(e)) from e
        return self._handle(resp)

    async def _delete(self, path: str, params: dict | None = None) -> None:
        try:
            async with self._new_http() as http:
                resp = await http.delete(path, headers=self._auth_headers(), params=params)
        except httpx.TransportError as e:
            raise PortainerAPIError(str(e)) from e
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("message", resp.text)
            except Exception:
                detail = resp.text
            raise PortainerAPIError(detail, resp.status_code)

    def _handle(self, resp: httpx.Response) -> Any:
        if resp.status_code == 204:
            return None
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("message", resp.text)
            except Exception:
                detail = resp.text
            raise PortainerAPIError(detail, resp.status_code)
        if not resp.content:
            return None
        return resp.json()
