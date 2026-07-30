<div align="center">

# 🔒 FRP Client GUI

**基于 Python 的 FRP 内网穿透客户端管理工具**

现代化暗色主题界面 · 多协议支持 · 一键启停 · 系统托盘驻留

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FRP](https://img.shields.io/badge/FRP-fatedier%2Ffrp-blue?logo=github)](https://github.com/fatedier/frp)

</div>

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🖥️ **服务器配置** | 可视化编辑服务器地址、端口、认证 Token |
| 🔀 **多协议支持** | 支持 9 种 FRP 代理类型，切换类型自动显示/隐藏对应配置字段 |
| ⚡ **一键启停** | 启动、停止 frpc 进程，实时显示运行状态 |
| 📋 **运行日志** | 彩色分级日志输出（info / success / warning / error） |
| 📌 **系统托盘** | 关闭窗口后最小化到托盘，支持托盘菜单退出 |
| 🛡️ **进程守护** | 程序退出时自动终止 frpc 进程，防止残留 |
| 💾 **配置持久化** | 所有配置自动保存到 `frp_config.json`，下次启动自动恢复 |

## 📋 支持的代理类型

| 类型 | 说明 | 额外字段 |
|------|------|----------|
| `tcp` | TCP 端口转发 | `remote_port`（远程端口） |
| `udp` | UDP 端口转发 | `remote_port`（远程端口） |
| `http` | HTTP 代理 | `subdomain` / `custom_domains` / `locations` / `http_headers` |
| `https` | HTTPS 代理 | 同 HTTP + `skip_tls_verify` |
| `stcp` | 安全 TCP（密钥认证） | `secret_key` / `custom_domains` |
| `sudp` | 安全 UDP（密钥认证） | `secret_key` / `custom_domains` |
| `xtcp` | P2P 穿透代理 | `secret_key` / `custom_domains` |
| `tcpmux` | TCP 多路复用 | `route_rule` / `http_user` / `http_password` |
| `httpconnect` | HTTP CONNECT 隧道 | `http_user` / `http_password` |

> 在界面中切换代理类型时，会自动显示/隐藏对应的额外配置字段。

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11

### 1. 下载 frpc

从 [FRP Releases](https://github.com/fatedier/frp/releases) 下载对应平台的 `frpc` 可执行文件，放置到项目根目录。

### 2. 安装依赖

```bash
pip install customtkinter pystray Pillow
```

### 3. 运行

```bash
python Start.py
```

## 📦 打包为 EXE

### 安装 PyInstaller

```bash
pip install pyinstaller
```

### 执行打包命令

```bash
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "FRP_Client" ^
    --icon "frpc.ico" ^
    --add-data "frpc.ico;." ^
    --add-data "frpc.exe;." ^
    --hidden-import "customtkinter" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    --clean ^
    Start.py
```

> **参数说明：**
>
> | 参数 | 作用 |
> |------|------|
> | `--onefile` | 打包为单个 EXE 文件 |
> | `--windowed` | 隐藏控制台窗口（GUI 程序） |
> | `--icon "frpc.ico"` | 设置 EXE 文件图标 |
> | `--add-data "frpc.ico;."` | 将 frpc.ico 嵌入打包（窗口/托盘图标） |
> | `--add-data "frpc.exe;."` | 将 frpc.exe 嵌入打包 |
> | `--hidden-import` | 显式声明隐式导入的库 |

### 打包后部署

将以下文件放在 `FRP_Client.exe` 同目录下：

```
FRP_Client.exe    # 打包后的程序
frpc.exe          # FRP 客户端（必须）
frpc.ico          # 应用图标（可选，打包时已嵌入）
frp_config.json   # 配置文件（首次运行自动生成）
```

## 📁 项目文件清单

```
FRP_Client/
├── Start.py            # 主程序源码（唯一 Python 文件）
├── frpc.exe            # FRP 客户端可执行文件（需自行放置）
├── frpc.ico            # 应用图标（窗口 + 托盘 + 打包）
├── frp_config.json     # 运行时配置（自动生成 / 手动编辑）
├── frpc.toml           # frpc 命令行配置（程序自动生成，无需手动编辑）
└── README.md           # 本文件
```

> ⚠️ `frpc.exe` 和 `frpc.ico` 为必需文件，需从 [FRP Releases](https://github.com/fatedier/frp/releases) 下载对应平台的 frpc 并放置到项目根目录。

## ⚙️ 配置文件说明

### frp_config.json

程序运行时读写的核心配置文件：

```json
{
  "server_addr": "your-server.com",
  "server_port": 7000,
  "token": "your-token",
  "frpc_path": "./frpc",
  "proxies": [
    {
      "name": "ssh",
      "type": "tcp",
      "local_ip": "127.0.0.1",
      "local_port": 22,
      "remote_port": 6000
    },
    {
      "name": "web-subdomain",
      "type": "http",
      "local_ip": "127.0.0.1",
      "local_port": 80,
      "remote_port": 80,
      "subdomain": "desk"
    },
    {
      "name": "web-custom",
      "type": "http",
      "local_ip": "127.0.0.1",
      "local_port": 8000,
      "remote_port": 80,
      "custom_domains": "example.com,www.example.com"
    },
    {
      "name": "db",
      "type": "stcp",
      "local_ip": "127.0.0.1",
      "local_port": 5432,
      "remote_port": 0,
      "secret_key": "my-secret-key"
    }
  ]
}
```

### 通用字段

| 字段 | 说明 |
|------|------|
| `server_addr` | FRP 服务器地址 |
| `server_port` | FRP 服务器端口（默认 7000） |
| `token` | 服务器认证令牌（可选） |
| `frpc_path` | frpc 可执行文件路径（默认 `./frpc`，Windows 下自动补全 `.exe`） |
| `proxies` | 代理规则数组 |

### 代理规则通用字段

| 字段 | 说明 |
|------|------|
| `name` | 规则名称（必填） |
| `type` | 代理类型 |
| `local_ip` | 本地地址（默认 `127.0.0.1`） |
| `local_port` | 本地端口（必填） |

### 各类型专属字段

<details>
<summary><b>TCP / UDP</b></summary>

| 字段 | 说明 |
|------|------|
| `remote_port` | 远程端口（必填） |

</details>

<details>
<summary><b>HTTP / HTTPS</b></summary>

| 字段 | 说明 |
|------|------|
| `subdomain` | 子域名（与 custom_domains 二选一） |
| `custom_domains` | 自定义域名，多个用逗号分隔 |
| `locations` | 路由路径，多个用逗号分隔（如 `/,/api`） |
| `http_headers` | HTTP 请求头匹配，格式 `key=value`，多个用逗号分隔 |
| `host_header_rewrite` | 重写 HTTP Host 头（可选） |
| `http_user` | HTTP Basic Auth 用户名（可选） |
| `http_password` | HTTP Basic Auth 密码（可选） |
| `skip_tls_verify` | 跳过 TLS 证书校验（仅 HTTPS，默认 `false`） |

</details>

<details>
<summary><b>STCP / SUDP / XTCP</b></summary>

| 字段 | 说明 |
|------|------|
| `secret_key` | 访问密钥（必填，用于安全认证） |
| `custom_domains` | 自定义域名，多个用逗号分隔 |

</details>

<details>
<summary><b>TCPMux</b></summary>

| 字段 | 说明 |
|------|------|
| `route_rule` | 路由规则（用于多路复用分流） |
| `http_user` | HTTP 用户名（可选） |
| `http_password` | HTTP 密码（可选） |
| `connect_timeout` | 连接超时秒数（默认 7） |
| `skip_tls_verify` | 跳过 TLS 证书校验（默认 `false`） |

</details>

<details>
<summary><b>HTTPConnect</b></summary>

| 字段 | 说明 |
|------|------|
| `http_user` | HTTP 用户名（可选） |
| `http_password` | HTTP 密码（可选） |
| `skip_tls_verify` | 跳过 TLS 证书校验（默认 `false`） |

</details>

### frpc.toml

由程序根据 `frp_config.json` 自动生成，供 frpc 读取，**无需手动编辑**。

## 🌐 HTTP 域名配置示例

### 方式一：子域名访问

假设 FRP 服务器配置了 `subDomainHost = "example.com"`：

```json
{
  "name": "desk",
  "type": "http",
  "local_ip": "127.0.0.1",
  "local_port": 8000,
  "remote_port": 80,
  "subdomain": "desk"
}
```

访问地址：`http://desk.example.com`

### 方式二：自定义域名访问

需要将 `yourdomain.com` 的 DNS 解析指向 FRP 服务器公网 IP：

```json
{
  "name": "web",
  "type": "http",
  "local_ip": "127.0.0.1",
  "local_port": 80,
  "remote_port": 80,
  "custom_domains": "yourdomain.com,www.yourdomain.com"
}
```

访问地址：`http://yourdomain.com`

### 方式三：带认证的域名访问

```json
{
  "name": "secure-web",
  "type": "http",
  "local_ip": "127.0.0.1",
  "local_port": 80,
  "remote_port": 80,
  "custom_domains": "secure.example.com",
  "http_user": "admin",
  "http_password": "your-password"
}
```

### 方式四：URL 路径路由

同一个域名不同路径指向不同服务：

```json
{
  "name": "api",
  "type": "http",
  "local_ip": "127.0.0.1",
  "local_port": 8080,
  "remote_port": 80,
  "custom_domains": "api.example.com",
  "locations": "/v1,/v2"
}
```

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + Q` | 退出程序（同时终止 frpc 进程） |

## 🛠️ 技术栈

| 库 | 用途 |
|----|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 现代化 tkinter UI 框架 |
| [pystray](https://github.com/moses-palmer/pystray) | 系统托盘支持 |
| [Pillow](https://python-pillow.org/) | 图像处理（加载 .ico 图标） |
| [FRP](https://github.com/fatedier/frp) | 快速反向代理工具 |

## 📄 许可证

[MIT License](LICENSE)
