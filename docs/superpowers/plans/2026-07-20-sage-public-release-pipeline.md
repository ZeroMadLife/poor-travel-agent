# Sage Public Release Pipeline 实施计划

> 日期：2026-07-20
> 基线：`dev/sage-v7@a60fcc4`
> 范围：公开静态门面的 CI、受限 ECS 发布、健康检查与回滚
> 域名 TLS 增量基线：`dev/sage-v7@9f9843e`

## 1. 问题

公开门面已经通过 ECS 的 `80` 端口可访问，但当前容器来自一次人工镜像导入和手工切换。
`dev/sage-v7` 后续更新只会进入 rootless Canary，公网入口不会自动继承；人工操作也缺少
不可变版本、候选健康检查、部署状态和一致的失败回滚。

## 2. 决策

沿用本机 `canaryctl` 作为 CI 判定和定时调度入口，不向 GitHub Actions 写入 ECS SSH 或
root 凭据。服务器新增 root-owned `public_releasectl`，只从标准输入接收严格 JSON：

```json
{"action":"apply","tag":"<40 位小写 commit SHA>"}
```

`sage-deploy` 只能通过固定 sudoers 命令无参数调用该控制器。控制器不能读取
`/etc/sage/env`，不能接收镜像名、容器名、端口、路径或 shell 文本。

## 3. 发布流

```text
dev/sage-v7 新 SHA
  -> python / backend-quality / frontend-quality / public-release 全绿
  -> 服务器 checkout 精确 SHA
  -> rootless deployctl 构建 sage-public:<SHA>
  -> public_releasectl 校验 OCI revision 与 65532:65532 用户
  -> 导入 root Docker
  -> 127.0.0.1:18081 候选容器 smoke
  -> 当前 live 停止并改名为 previous
  -> 新容器绑定 80/443，复用持久化 Caddy ACME volume
  -> 宿主机通过 /healthz 检查 HTTP 监听
  -> 本机等待 https://sagecompanion.top/ 证书与页面就绪
  -> 写入 current / previous / deployed_at
```

任一候选或切换健康检查失败时不写状态；切换已经开始则恢复 previous。外部 smoke 失败时，
`canaryctl` 请求显式回滚到控制器返回的上一完整 SHA。

## 4. CI 门禁

`frontend-quality` 同时执行主应用和 `build:public`。独立 `public-release` job 构建
`sage-public:${GITHUB_SHA}`，核验：

- OCI revision 等于精确 commit SHA；
- 默认用户为 `65532:65532`；
- rootfs 只读、drop `ALL` capabilities、`no-new-privileges`；
- 独立 bridge，不加入 private Canary 的 Compose 网络；浏览器侧继续由 CSP `connect-src none`
  禁止发起网络请求。容器级出站防火墙延后为独立主机安全切片，不能用会破坏端口发布的
  `--internal` 网络冒充已完成隔离；
- 静态首页包含预期标题且可从回环端口访问。

## 5. 一次性服务器安装

代码合入并同步到 `/opt/sage/app` 后，以 root 执行：

```bash
sh /opt/sage/app/infra/install/install-public-release-controller.sh /opt/sage/app
```

安装器会校验 Python、sudoers，并把控制器复制为 root-owned
`/usr/local/sbin/sage-public-releasectl`。public 发布状态单独保存在 root-only 的
`/var/lib/sage-public-release/state.json`，不会修改 private `deployctl` 使用的
`/opt/sage/state` 权限。日常状态查询不需要 root shell：

```bash
printf '%s\n' '{"action":"status"}' \
  | sudo -n /usr/local/sbin/sage-public-releasectl
```

显式回滚只接受已经存在的完整 SHA：

```bash
printf '%s\n' '{"action":"rollback","tag":"<previous SHA>"}' \
  | sudo -n /usr/local/sbin/sage-public-releasectl
```

## 6. 域名与 TLS 增量

`sagecompanion.top` 与 `www.sagecompanion.top` 都解析到 ECS 公网 IP。生产 Caddy 在非 root
用户下监听容器 `8081/8443`，由 root Docker 精确映射 ECS 私网网卡 `172.20.67.88` 的
`80/443`；HTTP 除 `/healthz` 之外固定跳转到原 Host 的 HTTPS。额外的
`127.0.0.1:18082` 只供控制器健康检查，避免与 `100.126.143.47:443` 的 Tailscale 私有入口
争用端口。`/data` 与 `/config` 使用 root Docker named volume，保证
证书、ACME account 与续期状态在容器替换和 previous 回滚之间保留。

候选 smoke、GitHub `public-release` job 与 private Canary 的 public 服务都显式使用
`Caddyfile.public-candidate`，只监听 HTTP 8081，不申请证书、不挂生产证书卷。只有受限的
root-owned `public_releasectl` 能启动生产 Caddy 配置。

域名正式在杭州 ECS 对公网提供服务前必须完成 ICP 备案；备案不由 CI/CD 自动化，也不能用
HTTPS 证书替代。安全组只开放公开门面所需的 TCP 80/443，不开放私人 Harness、数据库、
Redis 或 Docker 控制面。

## 7. 非目标与后续

- 不开放私人 Harness、API、PostgreSQL 或 Redis。
- 不把 root 密钥或服务器环境文件交给 GitHub Actions。
- 不在本切片实现 public-only Agent API；公开问答仍是独立静态、确定性体验。
- ICP 备案、公安联网备案与域名内容合规审核仍由站点所有者在阿里云控制台完成。
