#!/usr/bin/env python3
"""Root-owned, bounded release controller for the public Sage facade."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

_UTC = timezone.utc  # noqa: UP017 - the ECS host still runs Python 3.10.
COMMIT_TAG = re.compile(r"[0-9a-f]{40}")
IMAGE_REPOSITORY = "sage-public"
AGENT_IMAGE_REPOSITORY = "sage-public-agent"
LIVE_CONTAINER = "sage-public-gateway"
PREVIOUS_CONTAINER = "sage-public-gateway-previous"
CANDIDATE_CONTAINER = "sage-public-gateway-candidate"
LIVE_AGENT_CONTAINER = "sage-public-agent"
PREVIOUS_AGENT_CONTAINER = "sage-public-agent-previous"
CANDIDATE_AGENT_CONTAINER = "sage-public-agent-candidate"
PUBLIC_NETWORK = "sage-public-release"
PUBLIC_DATA_VOLUME = "sage-public-caddy-data"
PUBLIC_CONFIG_VOLUME = "sage-public-caddy-config"
PUBLIC_BIND_ADDRESS = "172.20.67.88"
DEFAULT_SOURCE_DOCKER_HOST = "unix:///run/user/1002/docker.sock"
DEFAULT_TARGET_DOCKER_HOST = "unix:///var/run/docker.sock"
DEFAULT_STATE_FILE = Path("/var/lib/sage-public-release/state.json")
DEFAULT_LOCK_FILE = Path("/run/lock/sage-public-release.lock")
DEFAULT_CANDIDATE_URL = "http://127.0.0.1:18081/"
DEFAULT_CANDIDATE_AGENT_URL = "http://127.0.0.1:18083/healthz"
DEFAULT_CANDIDATE_API_URL = "http://127.0.0.1:18081/api/public/v1/ask"
DEFAULT_LIVE_URL = "http://127.0.0.1:18082/healthz"
DEFAULT_AGENT_ENV_FILE = Path("/etc/sage/public-agent.env")
DEFAULT_AGENT_BUDGET_STATE_FILE = Path("/var/lib/sage-public-release/agent-budget.json")
AGENT_BUDGET_CONTAINER_PATH = "/var/lib/sage-public-agent/budget.json"


class PublicReleaseError(RuntimeError):
    """A bounded public release operation failed."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class PublicReleaseConfig:
    source_docker_host: str = DEFAULT_SOURCE_DOCKER_HOST
    target_docker_host: str = DEFAULT_TARGET_DOCKER_HOST
    state_file: Path = DEFAULT_STATE_FILE
    lock_file: Path = DEFAULT_LOCK_FILE
    candidate_url: str = DEFAULT_CANDIDATE_URL
    candidate_agent_url: str = DEFAULT_CANDIDATE_AGENT_URL
    candidate_api_url: str = DEFAULT_CANDIDATE_API_URL
    live_url: str = DEFAULT_LIVE_URL
    agent_env_file: Path = DEFAULT_AGENT_ENV_FILE
    agent_env_owner_uid: int = 0
    agent_budget_state_file: Path = DEFAULT_AGENT_BUDGET_STATE_FILE
    agent_runtime_uid: int = 65532


Runner = Callable[[Sequence[str], int], CommandResult]
HttpProbe = Callable[[str], bool]


def run_command(command: Sequence[str], timeout: int = 120) -> CommandResult:
    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(124, stderr=type(exc).__name__)
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def validate_tag(value: str) -> str:
    if COMMIT_TAG.fullmatch(value) is None:
        raise PublicReleaseError("发布版本必须是 40 位小写 Git commit SHA")
    return value


def parse_request(stream: TextIO) -> tuple[str, str | None]:
    raw = stream.read(2049)
    if len(raw) > 2048:
        raise PublicReleaseError("发布请求超过 2 KiB")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PublicReleaseError("发布请求不是有效 JSON") from exc
    if not isinstance(value, dict):
        raise PublicReleaseError("发布请求必须是 JSON object")
    action = value.get("action")
    allowed = {"status": {"action"}, "apply": {"action", "tag"}, "rollback": {"action", "tag"}}
    if not isinstance(action, str) or action not in allowed or set(value) != allowed[action]:
        raise PublicReleaseError("发布请求 action 或字段无效")
    tag = None if action == "status" else validate_tag(str(value["tag"]))
    return str(action), tag


def probe_http(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read(4096)
            return response.status == 200 and b"<title>" in body and b"Sage" in body
    except OSError:
        return False


def probe_agent_http(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            value = json.loads(response.read(4096))
            return (
                response.status == 200
                and isinstance(value, dict)
                and value.get("status") == "ready"
            )
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def probe_public_api(url: str) -> bool:
    request = urllib.request.Request(
        url,
        data=json.dumps({"question": "请用一句话说明 Sage 是什么。"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            value = json.loads(response.read(64 * 1024))
            if not isinstance(value, dict):
                return False
            receipt = value.get("receipt", {})
            return (
                response.status == 200
                and value.get("status") == "answered"
                and bool(value.get("citations"))
                and isinstance(receipt, dict)
                and bool(receipt.get("package_revision"))
            )
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


class PublicReleaseController:
    def __init__(
        self,
        config: PublicReleaseConfig,
        *,
        runner: Runner = run_command,
        http_probe: HttpProbe = probe_http,
        agent_probe: HttpProbe = probe_agent_http,
        api_probe: HttpProbe = probe_public_api,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.config = config
        self.runner = runner
        self.http_probe = http_probe
        self.agent_probe = agent_probe
        self.api_probe = api_probe
        self.clock = clock or (lambda: datetime.now(_UTC).isoformat())

    def _docker(self, host: str, *args: str, timeout: int = 120) -> CommandResult:
        result = self.runner(["docker", "--host", host, *args], timeout)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[-600:]
            raise PublicReleaseError("Docker 操作失败" + (f": {detail}" if detail else ""))
        return result

    def _target(self, *args: str, timeout: int = 120) -> CommandResult:
        return self._docker(self.config.target_docker_host, *args, timeout=timeout)

    @staticmethod
    def _container_args(
        name: str,
        image: str,
        bindings: Sequence[str],
        *,
        persistent_storage: bool,
        environment: Sequence[str] = (),
        command: Sequence[str] = (),
    ) -> list[str]:
        args = [
            "run",
            "-d",
            "--name",
            name,
            "--restart",
            "unless-stopped" if name == LIVE_CONTAINER else "no",
            "--network",
            PUBLIC_NETWORK,
            "--user",
            "65532:65532",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,mode=1777,size=8m",
            "--health-cmd",
            (
                "wget -qO- http://127.0.0.1:8081/healthz >/dev/null || exit 1"
                if persistent_storage
                else "wget -qO- http://127.0.0.1:8081/ >/dev/null || exit 1"
            ),
            "--health-interval",
            "15s",
            "--health-timeout",
            "5s",
            "--health-retries",
            "3",
        ]
        for binding in bindings:
            args.extend(("--publish", binding))
        for value in environment:
            args.extend(("--env", value))
        if persistent_storage:
            args.extend(
                (
                    "--mount",
                    f"type=volume,source={PUBLIC_DATA_VOLUME},target=/data",
                    "--mount",
                    f"type=volume,source={PUBLIC_CONFIG_VOLUME},target=/config",
                )
            )
        else:
            args.extend(
                (
                    "--tmpfs",
                    "/config:rw,noexec,nosuid,mode=1777,size=8m",
                    "--tmpfs",
                    "/data:rw,noexec,nosuid,mode=1777,size=8m",
                )
            )
        args.append(image)
        args.extend(command)
        return args

    def _agent_container_args(
        self,
        name: str,
        image: str,
        bindings: Sequence[str] = (),
        *,
        network_alias: str,
    ) -> list[str]:
        args = [
            "run",
            "-d",
            "--name",
            name,
            "--restart",
            "unless-stopped" if name == LIVE_AGENT_CONTAINER else "no",
            "--network",
            PUBLIC_NETWORK,
            "--network-alias",
            network_alias,
            "--user",
            "65532:65532",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,mode=1777,size=8m",
            "--env-file",
            str(self.config.agent_env_file),
            "--env",
            f"SAGE_PUBLIC_BUDGET_STATE_PATH={AGENT_BUDGET_CONTAINER_PATH}",
            "--mount",
            (
                "type=bind,source="
                f"{self.config.agent_budget_state_file},target={AGENT_BUDGET_CONTAINER_PATH}"
            ),
            "--health-cmd",
            (
                'python -c "import json,urllib.request; '
                "assert json.load(urllib.request.urlopen('http://127.0.0.1:8082/healthz', "
                "timeout=3))['status']=='ready'\""
            ),
            "--health-interval",
            "15s",
            "--health-timeout",
            "5s",
            "--health-retries",
            "3",
        ]
        for binding in bindings:
            args.extend(("--publish", binding))
        args.append(image)
        return args

    def _inspect_optional(self, name: str) -> bool:
        result = self.runner(
            ["docker", "--host", self.config.target_docker_host, "container", "inspect", name],
            30,
        )
        return result.returncode == 0

    def _container_tag(self, name: str, repository: str = IMAGE_REPOSITORY) -> str | None:
        result = self.runner(
            [
                "docker",
                "--host",
                self.config.target_docker_host,
                "container",
                "inspect",
                "--format",
                "{{.Config.Image}}",
                name,
            ],
            30,
        )
        if result.returncode != 0:
            return None
        image = result.stdout.strip()
        prefix = f"{repository}:"
        if not image.startswith(prefix):
            return None
        tag = image.removeprefix(prefix)
        return tag if COMMIT_TAG.fullmatch(tag) else None

    def _remove_optional(self, name: str) -> None:
        if self._inspect_optional(name):
            self._target("container", "rm", "--force", name, timeout=60)

    def _ensure_network(self) -> None:
        result = self.runner(
            [
                "docker",
                "--host",
                self.config.target_docker_host,
                "network",
                "inspect",
                "--format",
                "{{.Internal}} {{.Driver}}",
                PUBLIC_NETWORK,
            ],
            30,
        )
        if result.returncode == 0:
            if result.stdout.strip() != "false bridge":
                raise PublicReleaseError("公共门面 Docker 网络安全属性不匹配")
            return
        self._target("network", "create", "--driver", "bridge", PUBLIC_NETWORK)

    def _ensure_volume(self, name: str) -> None:
        result = self.runner(
            [
                "docker",
                "--host",
                self.config.target_docker_host,
                "volume",
                "inspect",
                "--format",
                "{{.Driver}}",
                name,
            ],
            30,
        )
        if result.returncode == 0:
            if result.stdout.strip() != "local":
                raise PublicReleaseError(f"公共门面 Docker volume {name} 驱动不匹配")
            return
        self._target("volume", "create", "--driver", "local", name)

    def _ensure_storage(self) -> None:
        self._ensure_volume(PUBLIC_DATA_VOLUME)
        self._ensure_volume(PUBLIC_CONFIG_VOLUME)

    def _verify_agent_env(self) -> None:
        try:
            stat = self.config.agent_env_file.stat()
        except OSError as exc:
            raise PublicReleaseError("公开 Agent 环境文件不存在") from exc
        if stat.st_uid != self.config.agent_env_owner_uid or stat.st_mode & 0o777 != 0o600:
            raise PublicReleaseError("公开 Agent 环境文件必须由 root 持有且权限为 0600")

    def _ensure_agent_budget_state(self) -> None:
        path = self.config.agent_budget_state_file
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink():
            raise PublicReleaseError("公开 Agent 预算账本不能是符号链接")
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        os.close(descriptor)
        os.chmod(path, 0o600)
        try:
            os.chown(path, self.config.agent_runtime_uid, -1)
        except PermissionError as exc:
            raise PublicReleaseError("无法设置公开 Agent 预算账本所有者") from exc
        if not path.is_file():
            raise PublicReleaseError("公开 Agent 预算账本不是普通文件")

    def _wait_healthy(self, url: str, attempts: int = 20) -> None:
        for _ in range(attempts):
            if self.http_probe(url):
                return
            time.sleep(0.25)
        raise PublicReleaseError("公共门面健康检查失败")

    def _wait_agent_healthy(self, url: str, attempts: int = 20) -> None:
        for _ in range(attempts):
            if self.agent_probe(url):
                return
            time.sleep(0.25)
        raise PublicReleaseError("公开 Agent 健康检查失败")

    def _wait_api_healthy(self, url: str, attempts: int = 3) -> None:
        for _ in range(attempts):
            if self.api_probe(url):
                return
            time.sleep(1)
        raise PublicReleaseError("公开 Agent 同源问答 smoke 失败")

    def _agent_container_healthy(self, name: str) -> bool:
        if not self._inspect_optional(name):
            return False
        result = self.runner(
            [
                "docker",
                "--host",
                self.config.target_docker_host,
                "container",
                "exec",
                name,
                "python",
                "-c",
                (
                    "import json,urllib.request; "
                    "assert json.load(urllib.request.urlopen("
                    "'http://127.0.0.1:8082/healthz',timeout=3))['status']=='ready'"
                ),
            ],
            30,
        )
        return result.returncode == 0

    def _load_state(self) -> dict[str, object]:
        if not self.config.state_file.is_file():
            return {}
        try:
            value = json.loads(self.config.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PublicReleaseError("公共发布状态文件损坏") from exc
        if not isinstance(value, dict):
            raise PublicReleaseError("公共发布状态文件格式无效")
        return value

    def _write_state(self, value: Mapping[str, object]) -> None:
        self.config.state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.config.state_file.with_suffix(".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.config.state_file)

    def _verify_image(self, host: str, tag: str, repository: str = IMAGE_REPOSITORY) -> str:
        image = f"{repository}:{validate_tag(tag)}"
        result = self._docker(
            host,
            "image",
            "inspect",
            "--format",
            '{{index .Config.Labels "org.opencontainers.image.revision"}} {{.Config.User}}',
            image,
            timeout=30,
        )
        if result.stdout.strip() != f"{tag} 65532:65532":
            raise PublicReleaseError("公共镜像 revision 或运行用户不匹配")
        return image

    def _import_image(self, tag: str, repository: str = IMAGE_REPOSITORY) -> str:
        image = self._verify_image(self.config.source_docker_host, tag, repository)
        with tempfile.NamedTemporaryFile(
            prefix=f"{repository}-", suffix=".tar", delete=False
        ) as stream:
            archive = Path(stream.name)
        try:
            os.chmod(archive, 0o600)
            saved = self.runner(
                [
                    "docker",
                    "--host",
                    self.config.source_docker_host,
                    "image",
                    "save",
                    "--output",
                    str(archive),
                    image,
                ],
                600,
            )
            if saved.returncode != 0:
                raise PublicReleaseError("导出公共镜像失败")
            self._target("image", "load", "--input", str(archive), timeout=600)
        finally:
            archive.unlink(missing_ok=True)
        return self._verify_image(self.config.target_docker_host, tag, repository)

    def _run_candidates(self, image: str, agent_image: str) -> None:
        self._verify_agent_env()
        self._ensure_agent_budget_state()
        self._remove_optional(CANDIDATE_AGENT_CONTAINER)
        self._remove_optional(CANDIDATE_CONTAINER)
        self._target(
            *self._agent_container_args(
                CANDIDATE_AGENT_CONTAINER,
                agent_image,
                ("127.0.0.1:18083:8082",),
                network_alias=CANDIDATE_AGENT_CONTAINER,
            )
        )
        self._target(
            *self._container_args(
                CANDIDATE_CONTAINER,
                image,
                ("127.0.0.1:18081:8081",),
                persistent_storage=False,
                environment=(f"SAGE_PUBLIC_AGENT_UPSTREAM={CANDIDATE_AGENT_CONTAINER}:8082",),
                command=(
                    "caddy",
                    "run",
                    "--config",
                    "/etc/caddy/Caddyfile.candidate",
                    "--adapter",
                    "caddyfile",
                ),
            )
        )
        try:
            self._wait_agent_healthy(self.config.candidate_agent_url)
            self._wait_api_healthy(self.config.candidate_api_url)
            self._wait_healthy(self.config.candidate_url)
        finally:
            self._remove_optional(CANDIDATE_CONTAINER)
            self._remove_optional(CANDIDATE_AGENT_CONTAINER)

    def _start_live(self, image: str, agent_image: str) -> None:
        self._verify_agent_env()
        self._ensure_agent_budget_state()
        self._ensure_storage()
        self._target(
            *self._agent_container_args(
                LIVE_AGENT_CONTAINER,
                agent_image,
                network_alias=LIVE_AGENT_CONTAINER,
            )
        )
        if not self._agent_container_healthy(LIVE_AGENT_CONTAINER):
            raise PublicReleaseError("公开 Agent 正式容器健康检查失败")
        self._target(
            *self._container_args(
                LIVE_CONTAINER,
                image,
                (
                    "127.0.0.1:18082:8081",
                    f"{PUBLIC_BIND_ADDRESS}:80:8081",
                    f"{PUBLIC_BIND_ADDRESS}:443:8443",
                ),
                persistent_storage=True,
            )
        )
        self._wait_healthy(self.config.live_url)

    def _restore_previous(self, *, agent_required: bool = False) -> bool:
        self._remove_optional(LIVE_CONTAINER)
        self._remove_optional(LIVE_AGENT_CONTAINER)
        if not self._inspect_optional(PREVIOUS_CONTAINER):
            raise PublicReleaseError("公共门面切换失败且没有可恢复容器")
        agent_enabled = self._inspect_optional(PREVIOUS_AGENT_CONTAINER)
        if agent_required and not agent_enabled:
            raise PublicReleaseError("上一版本要求公开 Agent，但恢复容器不存在")
        if agent_enabled:
            self._target("container", "rename", PREVIOUS_AGENT_CONTAINER, LIVE_AGENT_CONTAINER)
            self._target("container", "start", LIVE_AGENT_CONTAINER)
            if not self._agent_container_healthy(LIVE_AGENT_CONTAINER):
                raise PublicReleaseError("上一公开 Agent 容器恢复失败")
        self._target("container", "rename", PREVIOUS_CONTAINER, LIVE_CONTAINER)
        self._target("container", "start", LIVE_CONTAINER)
        self._wait_healthy(self.config.live_url)
        return agent_enabled

    def apply(self, tag: str) -> dict[str, object]:
        tag = validate_tag(tag)
        self._ensure_network()
        state = self._load_state()
        current = str(state.get("current") or "") or self._container_tag(LIVE_CONTAINER)
        live_agent_tag = self._container_tag(LIVE_AGENT_CONTAINER, AGENT_IMAGE_REPOSITORY)
        if (
            current == tag
            and live_agent_tag == tag
            and self.http_probe(self.config.live_url)
            and self._agent_container_healthy(LIVE_AGENT_CONTAINER)
        ):
            if state.get("current") != tag or state.get("agent_enabled") is not True:
                self._write_state(
                    {
                        "current": tag,
                        "previous": None,
                        "agent_enabled": True,
                        "deployed_at": self.clock(),
                    }
                )
            return {"status": "up-to-date", "tag": tag}
        image = self._import_image(tag)
        agent_image = self._import_image(tag, AGENT_IMAGE_REPOSITORY)
        self._run_candidates(image, agent_image)
        previous = current
        previous_agent_enabled = bool(current and live_agent_tag == current)
        self._remove_optional(PREVIOUS_CONTAINER)
        self._remove_optional(PREVIOUS_AGENT_CONTAINER)
        try:
            if self._inspect_optional(LIVE_CONTAINER):
                self._target("container", "stop", LIVE_CONTAINER, timeout=60)
                self._target("container", "rename", LIVE_CONTAINER, PREVIOUS_CONTAINER)
            if self._inspect_optional(LIVE_AGENT_CONTAINER):
                self._target("container", "stop", LIVE_AGENT_CONTAINER, timeout=60)
                self._target("container", "rename", LIVE_AGENT_CONTAINER, PREVIOUS_AGENT_CONTAINER)
            self._start_live(image, agent_image)
        except Exception:
            if self._inspect_optional(PREVIOUS_CONTAINER):
                self._restore_previous(agent_required=previous_agent_enabled)
            else:
                self._remove_optional(LIVE_CONTAINER)
                self._remove_optional(LIVE_AGENT_CONTAINER)
            raise
        deployed_at = self.clock()
        self._write_state(
            {
                "current": tag,
                "previous": previous,
                "previous_agent_enabled": previous_agent_enabled,
                "agent_enabled": True,
                "deployed_at": deployed_at,
            }
        )
        return {"status": "deployed", "tag": tag, "previous": previous, "deployed_at": deployed_at}

    def rollback(self, tag: str) -> dict[str, object]:
        tag = validate_tag(tag)
        self._ensure_network()
        state = self._load_state()
        current = str(state.get("current") or "") or self._container_tag(LIVE_CONTAINER)
        if self._container_tag(PREVIOUS_CONTAINER) == tag:
            agent_enabled = self._restore_previous(
                agent_required=state.get("previous_agent_enabled") is True
            )
            rolled_back_at = self.clock()
            self._write_state(
                {
                    "current": tag,
                    "previous": current,
                    "previous_agent_enabled": state.get("agent_enabled") is True,
                    "agent_enabled": agent_enabled,
                    "rolled_back_at": rolled_back_at,
                }
            )
            return {
                "status": "rolled-back",
                "tag": tag,
                "previous": current,
                "rolled_back_at": rolled_back_at,
            }
        image = self._verify_image(self.config.target_docker_host, tag)
        agent_image = self._verify_image(
            self.config.target_docker_host, tag, AGENT_IMAGE_REPOSITORY
        )
        self._run_candidates(image, agent_image)
        self._remove_optional(PREVIOUS_CONTAINER)
        self._remove_optional(PREVIOUS_AGENT_CONTAINER)
        try:
            if self._inspect_optional(LIVE_CONTAINER):
                self._target("container", "stop", LIVE_CONTAINER, timeout=60)
                self._target("container", "rename", LIVE_CONTAINER, PREVIOUS_CONTAINER)
            if self._inspect_optional(LIVE_AGENT_CONTAINER):
                self._target("container", "stop", LIVE_AGENT_CONTAINER, timeout=60)
                self._target("container", "rename", LIVE_AGENT_CONTAINER, PREVIOUS_AGENT_CONTAINER)
            self._start_live(image, agent_image)
        except Exception:
            if self._inspect_optional(PREVIOUS_CONTAINER):
                self._restore_previous(agent_required=state.get("agent_enabled") is True)
            else:
                self._remove_optional(LIVE_CONTAINER)
                self._remove_optional(LIVE_AGENT_CONTAINER)
            raise
        rolled_back_at = self.clock()
        self._write_state(
            {
                "current": tag,
                "previous": current,
                "previous_agent_enabled": state.get("agent_enabled") is True,
                "agent_enabled": True,
                "rolled_back_at": rolled_back_at,
            }
        )
        return {
            "status": "rolled-back",
            "tag": tag,
            "previous": current,
            "rolled_back_at": rolled_back_at,
        }

    def status(self) -> dict[str, object]:
        state = self._load_state()
        current = str(state.get("current") or "") or self._container_tag(LIVE_CONTAINER)
        agent_required = state.get("agent_enabled") is True or self._inspect_optional(
            LIVE_AGENT_CONTAINER
        )
        agent_healthy = (
            self._agent_container_healthy(LIVE_AGENT_CONTAINER) if agent_required else True
        )
        return {
            "status": (
                "healthy" if self.http_probe(self.config.live_url) and agent_healthy else "degraded"
            ),
            "current": current,
            "previous": state.get("previous"),
            "deployed_at": state.get("deployed_at", state.get("rolled_back_at")),
            "container": LIVE_CONTAINER if self._inspect_optional(LIVE_CONTAINER) else None,
            "agent_container": (
                LIVE_AGENT_CONTAINER if self._inspect_optional(LIVE_AGENT_CONTAINER) else None
            ),
        }

    def execute(self, action: str, tag: str | None) -> dict[str, object]:
        self.config.lock_file.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.config.lock_file, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(descriptor)
            raise PublicReleaseError("已有公共发布正在执行") from exc
        try:
            if action == "status":
                return self.status()
            if action == "apply" and tag is not None:
                return self.apply(tag)
            if action == "rollback" and tag is not None:
                return self.rollback(tag)
            raise PublicReleaseError("发布请求无效")
        finally:
            os.close(descriptor)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-docker-host", default=DEFAULT_SOURCE_DOCKER_HOST)
    parser.add_argument("--target-docker-host", default=DEFAULT_TARGET_DOCKER_HOST)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_FILE)
    parser.add_argument("--candidate-url", default=DEFAULT_CANDIDATE_URL)
    parser.add_argument("--candidate-agent-url", default=DEFAULT_CANDIDATE_AGENT_URL)
    parser.add_argument("--candidate-api-url", default=DEFAULT_CANDIDATE_API_URL)
    parser.add_argument("--live-url", default=DEFAULT_LIVE_URL)
    parser.add_argument("--agent-env-file", type=Path, default=DEFAULT_AGENT_ENV_FILE)
    parser.add_argument(
        "--agent-budget-state-file",
        type=Path,
        default=DEFAULT_AGENT_BUDGET_STATE_FILE,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        action, tag = parse_request(sys.stdin)
        result = PublicReleaseController(
            PublicReleaseConfig(
                source_docker_host=args.source_docker_host,
                target_docker_host=args.target_docker_host,
                state_file=args.state_file.resolve(),
                lock_file=args.lock_file.resolve(),
                candidate_url=args.candidate_url,
                candidate_agent_url=args.candidate_agent_url,
                candidate_api_url=args.candidate_api_url,
                live_url=args.live_url,
                agent_env_file=args.agent_env_file.resolve(),
                agent_budget_state_file=args.agent_budget_state_file.resolve(),
            )
        ).execute(action, tag)
    except PublicReleaseError as exc:
        print(f"public-releasectl blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
