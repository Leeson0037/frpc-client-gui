"""
FRP Client GUI — 内网穿透管理工具
现代化暗色主题界面 | 支持系统托盘 | 自动清理 frpc 进程
支持协议: TCP, UDP, HTTP, HTTPS, STCP, SUDP, XTCP, TCPMux, HTTPCONNECT
"""

import customtkinter as ctk
import subprocess
import threading
import json
import os
import sys
import atexit
import signal
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageTk


# ==================== 设计系统 ====================

# GitHub Dark 风格色板 — 深邃专业
COLORS = {
    # 背景层级
    "bg_deepest":      "#0D1117",   # 最深背景
    "bg_base":         "#161B22",   # 基础背景
    "bg_surface":      "#1C2128",   # 卡片表面
    "bg_elevated":     "#21262D",   # 悬浮/提升层
    "bg_overlay":      "#30363D",   # 覆盖层 / 分隔线

    # 主色（蓝色系）
    "primary":         "#58A6FF",   # 主操作色
    "primary_dim":     "#1F6FEB",   # 深主色
    "primary_subtle":  "#1C3A5E",   # 主色淡化底
    "primary_solid":   "#388BFD",   # 主色变体

    # 语义色
    "success":         "#3FB950",
    "success_subtle":  "#1A3325",   # 成功色淡化底
    "warning":         "#D29922",
    "warning_subtle":  "#3D2E0A",   # 警告色淡化底
    "danger":          "#F85149",
    "danger_subtle":   "#3D1A1A",   # 危险色淡化底

    # 文字层级
    "text_primary":    "#F0F6FC",
    "text_secondary":  "#8B949E",
    "text_muted":      "#484F58",
    "text_on_primary": "#FFFFFF",

    # 边框
    "border":          "#30363D",
    "border_active":   "#58A6FF",
    "border_subtle":   "#21262D",
}

# 全局字体配置
FONT_FAMILY = "Segoe UI"
FONT_MONO = "Cascadia Code, Consolas, monospace"


# ==================== 代理类型定义 ====================

# 支持的所有代理类型
PROXY_TYPES = ["tcp", "udp", "http", "https", "stcp", "sudp", "xtcp", "tcpmux", "httpconnect"]

# 各代理类型对应的额外字段（key, 显示名, placeholder, widget类型）
# widget_type: "entry" | "bool"
PROXY_EXTRA_FIELDS = {
    "http": [
        ("subdomain",       "子域名",     "例: fssc",          "entry"),
        ("custom_domains",  "自定义域名",  "多个用逗号分隔",      "entry"),
    ],
    "https": [
        ("subdomain",       "子域名",     "例: fssc",          "entry"),
        ("custom_domains",  "自定义域名",  "多个用逗号分隔",      "entry"),
        ("skip_tls_verify", "跳过TLS校验", "",                  "bool"),
    ],
    "stcp": [
        ("custom_domains",  "自定义域名",  "多个用逗号分隔",      "entry"),
        ("secret_key",      "密钥",       "访问密钥 (必填)",     "entry"),
    ],
    "sudp": [
        ("custom_domains",  "自定义域名",  "多个用逗号分隔",      "entry"),
        ("secret_key",      "密钥",       "访问密钥 (必填)",     "entry"),
    ],
    "xtcp": [
        ("custom_domains",  "自定义域名",  "多个用逗号分隔",      "entry"),
        ("secret_key",      "密钥",       "访问密钥 (必填)",     "entry"),
    ],
    "tcpmux": [
        ("route_rule",      "路由规则",    "必填",              "entry"),
        ("http_user",       "HTTP用户",   "可选",              "entry"),
        ("http_password",   "HTTP密码",   "可选",              "entry"),
    ],
    "httpconnect": [
        ("http_user",       "HTTP用户",   "可选",              "entry"),
        ("http_password",   "HTTP密码",   "可选",              "entry"),
    ],
}


# ==================== 工具函数 ====================

def get_base_dir():
    """获取程序运行的基础目录（兼容打包和开发环境）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_icon_path():
    """获取 frpc.ico 的完整路径"""
    return os.path.join(get_base_dir(), "frpc.ico")


def load_icon_image(size=64):
    """加载 frpc.ico 为 PIL Image，失败则返回纯色备用图标"""
    path = get_icon_path()
    if os.path.exists(path):
        try:
            img = Image.open(path)
            img = img.resize((size, size), Image.LANCZOS)
            return img
        except Exception:
            pass
    return Image.new("RGB", (size, size), color=(88, 166, 255))


# ==================== 配置管理 ====================

CONFIG_FILE = "frp_config.json"

DEFAULT_CONFIG = {
    "server_addr": "127.0.0.1",
    "server_port": 7000,
    "token": "",
    "proxies": [
        {"name": "ssh", "type": "tcp", "local_ip": "127.0.0.1", "local_port": 22, "remote_port": 6000}
    ]
}


def load_config():
    path = os.path.join(get_base_dir(), CONFIG_FILE)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    path = os.path.join(get_base_dir(), CONFIG_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def generate_frpc_toml(config, output_path=None):
    """从配置字典生成 frpc.toml 文件 — 支持所有代理类型"""
    if output_path is None:
        output_path = os.path.join(get_base_dir(), "frpc.toml")
    lines = []
    lines.append(f'serverAddr = "{config["server_addr"]}"')
    lines.append(f'serverPort = {config["server_port"]}')
    if config.get("token"):
        lines.append(f'auth.token = "{config["token"]}"')
    lines.append("")

    for proxy in config.get("proxies", []):
        ptype = proxy.get("type", "tcp")
        lines.append("[[proxies]]")
        lines.append(f'name = "{proxy["name"]}"')
        lines.append(f'type = "{ptype}"')
        lines.append(f'localIP = "{proxy.get("local_ip", "127.0.0.1")}"')
        lines.append(f'localPort = {proxy.get("local_port", 0)}')

        if ptype in ("tcp", "udp"):
            lines.append(f'remotePort = {proxy.get("remote_port", 0)}')

        elif ptype in ("http", "https"):
            subdomain = proxy.get("subdomain", "")
            if subdomain:
                lines.append(f'subdomain = "{subdomain}"')
            custom_domains = proxy.get("custom_domains", "")
            if custom_domains:
                domains_list = [d.strip() for d in custom_domains.split(",") if d.strip()]
                if domains_list:
                    formatted = ", ".join(f'"{d}"' for d in domains_list)
                    lines.append(f'customDomains = [{formatted}]')
            locations = proxy.get("locations", "")
            if locations:
                loc_list = [l.strip() for l in locations.split(",") if l.strip()]
                if loc_list:
                    formatted = ", ".join(f'"{l}"' for l in loc_list)
                    lines.append(f'locations = [{formatted}]')
            headers = proxy.get("http_headers", "")
            if headers:
                lines.append("[proxies.headers]")
                for h in headers.split(","):
                    h = h.strip()
                    if "=" in h:
                        k, v = h.split("=", 1)
                        lines.append(f'{k.strip()} = "{v.strip()}"')
            host_rewrite = proxy.get("host_header_rewrite", "")
            if host_rewrite:
                lines.append(f'hostHeaderRewrite = "{host_rewrite}"')
            http_user = proxy.get("http_user", "")
            if http_user:
                lines.append(f'httpUser = "{http_user}"')
            http_password = proxy.get("http_password", "")
            if http_password:
                lines.append(f'httpPassword = "{http_password}"')
            if ptype == "https":
                skip = proxy.get("skip_tls_verify", False)
                if skip:
                    lines.append("skipTLSVerify = true")

        elif ptype in ("stcp", "sudp", "xtcp"):
            custom_domains = proxy.get("custom_domains", "")
            if custom_domains:
                domains_list = [d.strip() for d in custom_domains.split(",") if d.strip()]
                if domains_list:
                    formatted = ", ".join(f'"{d}"' for d in domains_list)
                    lines.append(f'customDomains = [{formatted}]')
            secret_key = proxy.get("secret_key", "")
            if secret_key:
                lines.append(f'secretKey = "{secret_key}"')

        elif ptype == "tcpmux":
            route_rule = proxy.get("route_rule", "")
            if route_rule:
                lines.append(f'routeRule = "{route_rule}"')
            http_user = proxy.get("http_user", "")
            if http_user:
                lines.append(f'httpUser = "{http_user}"')
            http_password = proxy.get("http_password", "")
            if http_password:
                lines.append(f'httpPassword = "{http_password}"')
            connect_timeout = proxy.get("connect_timeout", "")
            if connect_timeout and connect_timeout.isdigit():
                lines.append(f'connectTimeout = {connect_timeout}')
            skip = proxy.get("skip_tls_verify", False)
            if skip:
                lines.append("skipTLSVerify = true")

        elif ptype == "httpconnect":
            http_user = proxy.get("http_user", "")
            if http_user:
                lines.append(f'httpUser = "{http_user}"')
            http_password = proxy.get("http_password", "")
            if http_password:
                lines.append(f'httpPassword = "{http_password}"')
            skip = proxy.get("skip_tls_verify", False)
            if skip:
                lines.append("skipTLSVerify = true")

        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path


# ==================== FRP 核心控制器 ====================

class FRPController:
    """管理 frpc 子进程的生命周期"""

    def __init__(self, log_callback):
        self.process = None
        self.log_callback = log_callback
        self.frpc_path = ""

    def start(self, config_path: str):
        if self.is_running():
            self.log_callback("[警告] FRP 已在运行中", "warning")
            return

        if not os.path.exists(self.frpc_path):
            self.log_callback(f"[错误] 未找到 frpc: {self.frpc_path}", "error")
            return

        try:
            cmd = [self.frpc_path, "-c", config_path]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            threading.Thread(target=self._read_output, daemon=True).start()
            self.log_callback(f"[启动] FRP 已启动  PID={self.process.pid}", "success")
        except Exception as e:
            self.log_callback(f"[错误] 启动失败: {e}", "error")

    def stop(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
            self.log_callback("[停止] FRP 已停止", "warning")
            self.process = None
        elif self.process:
            self.process = None

    def force_kill(self):
        """强制终止 — 用于程序退出时的紧急清理"""
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
                self.process.wait(timeout=3)
            except Exception:
                pass
            self.process = None

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def _read_output(self):
        proc = self.process
        if not proc or not proc.stdout:
            return
        for line in iter(proc.stdout.readline, ""):
            if line:
                self.log_callback(line.rstrip())


# ==================== 系统托盘 ====================

class TrayManager:
    def __init__(self, app):
        self.app = app
        self.icon = None
        img = load_icon_image(64)
        self.icon = Icon(
            "FRP Client", img, "FRP Client",
            menu=Menu(
                MenuItem("显示窗口", self.show_window, default=True),
                MenuItem("退出程序", self.quit_app),
            ),
        )

    def show_window(self, icon=None, item=None):
        self.app.after(0, self.app.deiconify)
        self.app.after(0, self.app.lift)
        self.app.after(0, lambda: self.app.focus_force())

    def quit_app(self, icon=None, item=None):
        self.app.after(0, self.app._full_exit)

    def run(self):
        threading.Thread(target=self.icon.run, daemon=True).start()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass


# ==================== 代理类型显示名和颜色 ====================

PROXY_TYPE_LABELS = {
    "tcp": "TCP 端口转发",
    "udp": "UDP 端口转发",
    "http": "HTTP 代理",
    "https": "HTTPS 代理",
    "stcp": "安全 TCP",
    "sudp": "安全 UDP",
    "xtcp": "P2P 穿透",
    "tcpmux": "TCP 多路复用",
    "httpconnect": "HTTP 隧道",
}

PROXY_TYPE_COLORS = {
    "tcp": ("#3FB950", "#1A3325"),      # 绿色
    "udp": ("#58A6FF", "#1C3A5E"),      # 蓝色
    "http": ("#D29922", "#3D2E0A"),     # 金色
    "https": ("#A371F7", "#2D1A5E"),    # 紫色
    "stcp": ("#F97583", "#3D1A1A"),     # 红色
    "sudp": ("#58A6FF", "#1C3A5E"),     # 蓝色
    "xtcp": ("#FF7B72", "#3D1A1A"),     # 橙红
    "tcpmux": ("#56D364", "#1A3325"),   # 浅绿
    "httpconnect": ("#BC8CFF", "#2D1A5E"),  # 浅紫
}


def _make_labeled_entry(parent, label_text, placeholder, width=130, entry_key=None, initial="", extra_entries=None):
    """创建带标签的输入框组件"""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(side="left", padx=(0, 10))
    
    # 标签
    ctk.CTkLabel(
        frame, text=label_text,
        font=(FONT_FAMILY, 10),
        text_color=COLORS["text_secondary"],
    ).pack(side="left", padx=(0, 4))
    
    # 输入框
    entry = ctk.CTkEntry(
        frame, placeholder_text=placeholder, width=width, height=26,
        corner_radius=4, font=(FONT_FAMILY, 11),
        border_color=COLORS["border"],
    )
    entry.insert(0, initial)
    entry.pack(side="left")
    
    if entry_key and extra_entries is not None:
        extra_entries[entry_key] = entry
    return entry


def _make_labeled_checkbox(parent, label_text, key, initial=False, extra_bools=None):
    """创建带标签的复选框组件"""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(side="left", padx=(0, 10))
    
    # 标签
    ctk.CTkLabel(
        frame, text=label_text,
        font=(FONT_FAMILY, 10),
        text_color=COLORS["text_secondary"],
    ).pack(side="left", padx=(0, 4))
    
    # 复选框
    checkbox = ctk.CTkCheckBox(
        frame, text="", width=20, height=26,
        font=(FONT_FAMILY, 11),
        fg_color=COLORS["primary_dim"],
        hover_color=COLORS["primary"],
    )
    if initial:
        checkbox.select()
    checkbox.pack(side="left")
    
    if extra_bools is not None:
        extra_bools[key] = checkbox
    return checkbox


# ==================== 端口映射行 ====================

class ProxyRow(ctk.CTkFrame):
    """一行端口映射规则 — 支持所有 FRP 代理类型的动态字段"""

    def __init__(self, parent, proxy_data, on_delete, index=0):
        super().__init__(parent, fg_color=COLORS["bg_surface"],
                         corner_radius=8, border_width=1,
                         border_color=COLORS["border"])
        self.on_delete = on_delete
        self.extra_entries = {}
        self.extra_bools = {}
        self.pack(fill="x", pady=4, padx=2)
        
        ptype = proxy_data.get("type", "tcp")
        type_color, type_bg = PROXY_TYPE_COLORS.get(ptype, (COLORS["text_secondary"], COLORS["bg_elevated"]))

        # ─── 主行 ───
        main_row = ctk.CTkFrame(self, fg_color="transparent")
        main_row.pack(fill="x", padx=10, pady=(10, 4))

        # 序号
        self.index_label = ctk.CTkLabel(
            main_row, text=f"#{index + 1}", width=30,
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_secondary"]
        )
        self.index_label.pack(side="left", padx=(0, 6))

        # 名称输入框（带标签）
        name_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        name_frame.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(name_frame, text="名称", font=(FONT_FAMILY, 10), text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 4))
        self.name_entry = ctk.CTkEntry(name_frame, placeholder_text="规则名称", width=80, height=26, corner_radius=4, font=(FONT_FAMILY, 11), border_color=COLORS["border"])
        self.name_entry.insert(0, proxy_data.get("name", ""))
        self.name_entry.pack(side="left")

        # 协议类型下拉框（带标签）
        type_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        type_frame.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(type_frame, text="类型", font=(FONT_FAMILY, 10), text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 4))
        self.type_combo = ctk.CTkComboBox(
            type_frame, values=PROXY_TYPES, width=85, height=26,
            corner_radius=4, font=(FONT_FAMILY, 11),
            border_color=COLORS["border"],
            state="readonly",
            button_color=COLORS["primary_dim"],
            button_hover_color=COLORS["primary"],
            dropdown_fg_color=COLORS["bg_elevated"],
            command=self._on_type_changed,
        )
        self.type_combo.set(ptype)
        self.type_combo.pack(side="left")

        # 本地地址（带标签）
        local_ip_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        local_ip_frame.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(local_ip_frame, text="本地", font=(FONT_FAMILY, 10), text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 4))
        self.local_ip_entry = ctk.CTkEntry(local_ip_frame, placeholder_text="127.0.0.1", width=100, height=26, corner_radius=4, font=(FONT_FAMILY, 11), border_color=COLORS["border"])
        self.local_ip_entry.insert(0, proxy_data.get("local_ip", "127.0.0.1"))
        self.local_ip_entry.pack(side="left")

        # 冒号
        ctk.CTkLabel(main_row, text=":", width=8,
                      font=(FONT_FAMILY, 13, "bold"),
                      text_color=COLORS["text_muted"]).pack(side="left", padx=0)

        # 本地端口（带标签）
        local_port_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        local_port_frame.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(local_port_frame, text="端口", font=(FONT_FAMILY, 10), text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 4))
        self.local_port_entry = ctk.CTkEntry(local_port_frame, placeholder_text="端口", width=55, height=26, corner_radius=4, font=(FONT_FAMILY, 11), border_color=COLORS["border"])
        self.local_port_entry.insert(0, str(proxy_data.get("local_port", "")))
        self.local_port_entry.pack(side="left")

        # 箭头
        self.arrow_label = ctk.CTkLabel(
            main_row, text="  →  ", width=30,
            font=(FONT_FAMILY, 14, "bold"),
            text_color=COLORS["primary"]
        )
        self.arrow_label.pack(side="left")

        # 远程端口（带标签）
        self.remote_port_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        self.remote_port_frame.pack(side="left")
        ctk.CTkLabel(self.remote_port_frame, text="远程", font=(FONT_FAMILY, 10), text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 4))
        self.remote_port_entry = ctk.CTkEntry(
            self.remote_port_frame, placeholder_text="端口", width=55, height=26,
            corner_radius=4, font=(FONT_FAMILY, 11),
            border_color=COLORS["border"]
        )
        self.remote_port_entry.insert(0, str(proxy_data.get("remote_port", "")))
        self.remote_port_entry.pack(side="left")

        # 删除按钮
        del_btn = ctk.CTkButton(
            main_row, text="✕", width=30, height=26,
            corner_radius=4,
            fg_color="transparent",
            hover_color=COLORS["danger_subtle"],
            text_color=COLORS["danger"],
            font=(FONT_FAMILY, 13, "bold"),
            command=self._delete,
        )
        del_btn.pack(side="left", padx=(8, 0))

        # ─── 额外字段容器（根据类型动态生成） ───
        self.extra_fields_frame = ctk.CTkFrame(
            self, 
            fg_color=type_bg,
            corner_radius=6,
            border_width=1,
            border_color=type_color
        )
        self.extra_fields_frame.pack(fill="x", padx=10, pady=(0, 8))

        # 根据当前类型更新字段
        self._update_extra_fields(proxy_data)

    # ---------- 动态字段管理 ----------

    def _clear_extra_fields(self):
        """清空额外字段容器"""
        for w in self.extra_fields_frame.winfo_children():
            w.destroy()
        self.extra_entries.clear()
        self.extra_bools.clear()

    def _on_type_changed(self, _event=None):
        """代理类型变更时，重新生成额外字段"""
        old_data = self.get_data()
        self._update_extra_fields(old_data)
        
        # 更新边框颜色
        ptype = self.type_combo.get()
        type_color, type_bg = PROXY_TYPE_COLORS.get(ptype, (COLORS["text_secondary"], COLORS["bg_elevated"]))
        self.extra_fields_frame.configure(fg_color=type_bg, border_color=type_color)
        
        # 确保 extra_fields_frame 可见
        self.extra_fields_frame.pack(fill="x", padx=10, pady=(0, 8))

    def _update_extra_fields(self, proxy_data=None):
        """根据当前代理类型，重建额外字段"""
        if proxy_data is None:
            proxy_data = {}
        ptype = self.type_combo.get()

        self._clear_extra_fields()

        extra_fields = PROXY_EXTRA_FIELDS.get(ptype, [])

        # 根据代理类型决定是否显示远程端口
        if ptype in ("tcp", "udp", "stcp", "sudp", "xtcp"):
            self.arrow_label.pack(side="left")
            self.remote_port_frame.pack(side="left")
        else:
            self.arrow_label.pack_forget()
            self.remote_port_frame.pack_forget()

        if not extra_fields:
            # tcp / udp 无额外字段，隐藏容器
            self.extra_fields_frame.pack_forget()
            return

        # 类型提示标签
        type_label = PROXY_TYPE_LABELS.get(ptype, ptype.upper())
        ctk.CTkLabel(
            self.extra_fields_frame,
            text=f"  {type_label} 配置：",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left", padx=(0, 10))

        # 生成字段
        for field_key, label, placeholder, widget_type in extra_fields:
            initial = proxy_data.get(field_key, "")
            if widget_type == "bool":
                _make_labeled_checkbox(
                    self.extra_fields_frame, label, field_key,
                    initial=bool(initial), extra_bools=self.extra_bools
                )
            else:
                _make_labeled_entry(
                    self.extra_fields_frame, label, placeholder,
                    width=110, entry_key=field_key, initial=str(initial),
                    extra_entries=self.extra_entries
                )

    # ---------- 数据提取 ----------

    def get_data(self):
        """提取所有输入框的数据"""
        raw = {
            "name": self.name_entry.get().strip(),
            "type": self.type_combo.get(),
            "local_ip": self.local_ip_entry.get().strip() or "127.0.0.1",
            "local_port": 0,
            "remote_port": 0,
        }
        
        lp = self.local_port_entry.get().strip()
        rp = self.remote_port_entry.get().strip()
        if lp.isdigit():
            raw["local_port"] = int(lp)
        if rp.isdigit():
            raw["remote_port"] = int(rp)

        # 收集所有额外的 entry 字段
        for key, entry in self.extra_entries.items():
            val = entry.get().strip()
            if val:
                raw[key] = val

        # 收集所有额外的 bool 字段
        for key, checkbox in self.extra_bools.items():
            raw[key] = checkbox.get() == 1

        return raw

    def _delete(self):
        self.on_delete(self)


# ==================== 主界面 ====================

class FRPGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 窗口基础 ---
        self.title("FRP Client — 内网穿透管理")
        self.geometry("960x740")
        self.minsize(860, 680)
        self.configure(fg_color=COLORS["bg_deepest"])

        # 设置窗口图标
        self._set_window_icon()

        # 外观
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- 数据 ---
        self.config_data = load_config()
        self.proxy_rows = []
        self._frp_controller = FRPController(self._append_log)

        # --- 构建界面 ---
        self._build_ui()

        # --- 系统托盘 ---
        self.tray = TrayManager(self)
        self.tray.run()

        # --- 进程清理注册 ---
        self._cleanup_registered = False
        self._register_cleanup()

        # --- 窗口事件 ---
        self.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        self.bind("<Control-q>", lambda e: self._full_exit())

        # 恢复已保存的代理行
        self._load_proxies_from_config()

        # 启动状态轮询
        self._poll_status()

    def _set_window_icon(self):
        """设置窗口图标（frpc.ico）"""
        ico_path = get_icon_path()
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

    def _register_cleanup(self):
        """注册程序退出时的清理逻辑"""
        if self._cleanup_registered:
            return
        self._cleanup_registered = True

        # atexit — 确保 Python 正常退出时清理
        atexit.register(self._emergency_cleanup)

        # signal — Unix 信号（Ctrl+C 等）
        if os.name != "nt":
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda s, f: self._full_exit())

    def _emergency_cleanup(self):
        """紧急清理 — 只杀 frpc 进程"""
        self._frp_controller.force_kill()

    # ==================== UI 构建 ====================

    def _build_ui(self):
        # 主容器
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=12, pady=10)

        # 顶部栏
        self._build_header(main)

        # 上下分割 — 配置区 + 日志区
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=3)
        main.rowconfigure(2, weight=2)

        self._build_config_section(main)
        self._build_log_section(main)

    def _build_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            header, text="⚡  FRP Client",
            font=(FONT_FAMILY, 18, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkLabel(
            header, text="内网穿透管理工具",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(8, 0), pady=(4, 0))

        # 状态指示
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right")

        self.status_dot = ctk.CTkLabel(
            status_frame, text="●", width=16,
            font=(FONT_FAMILY, 14),
            text_color=COLORS["text_muted"],
        )
        self.status_dot.pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_frame, text="未运行",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["text_muted"],
        )
        self.status_label.pack(side="left", padx=(2, 0))

    # ---------- 配置面板 ----------

    def _build_config_section(self, parent):
        # 外层卡片
        card = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_base"],
            corner_radius=10, border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(fill="x", pady=(0, 0))

        # 卡片标题
        title_bar = ctk.CTkFrame(card, fg_color="transparent")
        title_bar.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            title_bar, text="⚙  服务器配置",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # --- 服务器地址行 ---
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(4, 4))

        ctk.CTkLabel(row1, text="服务器地址", width=80, anchor="w",
                      font=(FONT_FAMILY, 12),
                      text_color=COLORS["text_secondary"]).pack(side="left")

        self.server_addr_entry = ctk.CTkEntry(
            row1, placeholder_text="例如 123.123.123.123",
            height=34, corner_radius=6, font=(FONT_FAMILY, 12),
            border_color=COLORS["border"],
        )
        self.server_addr_entry.insert(0, self.config_data.get("server_addr", ""))
        self.server_addr_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkLabel(row1, text="端口", width=35, anchor="w",
                      font=(FONT_FAMILY, 12),
                      text_color=COLORS["text_secondary"]).pack(side="left")

        self.server_port_entry = ctk.CTkEntry(
            row1, placeholder_text="7000", width=80,
            height=34, corner_radius=6, font=(FONT_FAMILY, 12),
            border_color=COLORS["border"],
        )
        self.server_port_entry.insert(0, str(self.config_data.get("server_port", "")))
        self.server_port_entry.pack(side="left", padx=0)

        # --- Token 行 ---
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(row2, text="认证 Token", width=80, anchor="w",
                      font=(FONT_FAMILY, 12),
                      text_color=COLORS["text_secondary"]).pack(side="left")

        self.token_entry = ctk.CTkEntry(
            row2, placeholder_text="服务器认证令牌（可选）",
            show="•", height=34, corner_radius=6,
            font=(FONT_FAMILY, 12), border_color=COLORS["border"],
        )
        self.token_entry.insert(0, self.config_data.get("token", ""))
        self.token_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.token_btn = ctk.CTkButton(
            row2, text="👁", width=36, height=34,
            corner_radius=6, font=(FONT_FAMILY, 14),
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["bg_overlay"],
            text_color=COLORS["text_secondary"],
            command=self._toggle_token,
        )
        self.token_btn.pack(side="left")

        # --- frpc 路径行 ---
        row_path = ctk.CTkFrame(card, fg_color="transparent")
        row_path.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(row_path, text="frpc 路径", width=80, anchor="w",
                      font=(FONT_FAMILY, 12),
                      text_color=COLORS["text_secondary"]).pack(side="left")

        self.frpc_path_entry = ctk.CTkEntry(
            row_path, placeholder_text="frpc 可执行文件路径",
            height=34, corner_radius=6, font=(FONT_FAMILY, 12),
            border_color=COLORS["border"],
        )
        self.frpc_path_entry.insert(0, self.config_data.get("frpc_path", "./frpc"))
        self.frpc_path_entry.pack(side="left", fill="x", expand=True)

        # ─── 端口映射规则区 ───
        sep2 = ctk.CTkFrame(card, height=1, fg_color=COLORS["border"])
        sep2.pack(fill="x", padx=16, pady=(4, 4))

        rule_header = ctk.CTkFrame(card, fg_color="transparent")
        rule_header.pack(fill="x", padx=16, pady=(4, 4))

        ctk.CTkLabel(
            rule_header, text="端口映射规则",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # 协议提示标签
        ctk.CTkLabel(
            rule_header,
            text="TCP · UDP · HTTP · HTTPS · STCP · SUDP · XTCP · TCPMux · HTTPConnect",
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(12, 0))

        self.add_rule_btn = ctk.CTkButton(
            rule_header, text="＋ 添加规则", width=100, height=30,
            corner_radius=6, font=(FONT_FAMILY, 12),
            fg_color=COLORS["primary_subtle"],
            hover_color=COLORS["primary_solid"],
            text_color=COLORS["primary"],
            border_width=1,
            border_color=COLORS["primary_dim"],
            command=self._add_proxy_row,
        )
        self.add_rule_btn.pack(side="right")

        # 代理行容器（带滚动）
        self.proxy_scroll = ctk.CTkScrollableFrame(
            card, fg_color=COLORS["bg_surface"],
            corner_radius=8, height=160,
            scrollbar_button_color=COLORS["bg_overlay"],
            scrollbar_button_hover_color=COLORS["border"],
        )
        self.proxy_scroll.pack(fill="x", padx=16, pady=(0, 8))

        # ─── 操作按钮区 ───
        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 12))

        self.start_btn = ctk.CTkButton(
            btn_bar, text="▶  启动连接", width=130, height=36,
            corner_radius=8, font=(FONT_FAMILY, 13, "bold"),
            fg_color=COLORS["success"],
            hover_color="#2EA043",
            text_color=COLORS["text_on_primary"],
            command=self.start_frp,
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            btn_bar, text="■  停止", width=100, height=36,
            corner_radius=8, font=(FONT_FAMILY, 13, "bold"),
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["danger_subtle"],
            text_color=COLORS["danger"],
            border_width=1,
            border_color=COLORS["border"],
            command=self.stop_frp,
        )
        self.stop_btn.pack(side="left", padx=(0, 8))

        self.save_btn = ctk.CTkButton(
            btn_bar, text="💾  保存配置", width=110, height=36,
            corner_radius=8, font=(FONT_FAMILY, 13),
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["bg_overlay"],
            text_color=COLORS["text_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._save_config_ui,
        )
        self.save_btn.pack(side="left")

    # ---------- 日志面板 ----------

    def _build_log_section(self, parent):
        log_card = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_base"],
            corner_radius=10, border_width=1,
            border_color=COLORS["border"],
        )
        log_card.pack(fill="both", expand=True, pady=(0, 0))

        # 标题栏
        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            log_header, text="📋  运行日志",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            log_header, text="清空", width=56, height=26,
            corner_radius=6, font=(FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=COLORS["bg_elevated"],
            text_color=COLORS["text_muted"],
            command=self._clear_log,
        )
        clear_btn.pack(side="right")

        # 日志文本框
        self.log_textbox = ctk.CTkTextbox(
            log_card,
            font=(FONT_MONO, 12),
            fg_color=COLORS["bg_deepest"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_subtle"],
            text_color=COLORS["text_secondary"],
            scrollbar_button_color=COLORS["bg_overlay"],
            scrollbar_button_hover_color=COLORS["border"],
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    # ==================== 代理行管理 ====================

    def _add_proxy_row(self, data=None):
        if data is None:
            data = {
                "name": "", "type": "tcp", "local_ip": "127.0.0.1",
                "local_port": "", "remote_port": ""
            }
        idx = len(self.proxy_rows)
        row = ProxyRow(self.proxy_scroll, data, self._remove_proxy_row, idx)
        self.proxy_rows.append(row)
        self._refresh_row_indices()

    def _remove_proxy_row(self, row):
        row.pack_forget()
        row.destroy()
        if row in self.proxy_rows:
            self.proxy_rows.remove(row)
        self._refresh_row_indices()

    def _refresh_row_indices(self):
        for i, row in enumerate(self.proxy_rows):
            if hasattr(row, "index_label"):
                row.index_label.configure(text=f"#{i + 1}")

    def _load_proxies_from_config(self):
        for p in self.config_data.get("proxies", []):
            self._add_proxy_row(p)

    # ==================== 配置读写 ====================

    def _collect_config_from_ui(self):
        proxies = []
        for row in self.proxy_rows:
            d = row.get_data()
            ptype = d.get("type", "tcp")

            # 基本验证：名称必填
            if not d["name"]:
                continue

            if ptype in ("tcp", "udp"):
                # TCP/UDP 需要 local_port 和 remote_port
                if d["local_port"] > 0 and d["remote_port"] > 0:
                    proxies.append(d)
            elif ptype in ("http", "https"):
                # HTTP/HTTPS 需要 local_port，remote_port 可选
                if d["local_port"] > 0:
                    proxies.append(d)
            elif ptype in ("stcp", "sudp", "xtcp"):
                # STCP/SUDP/XTCP 需要 local_port 和 secret_key
                if d["local_port"] > 0 and d.get("secret_key"):
                    proxies.append(d)
            elif ptype == "tcpmux":
                # TCPMux 需要 local_port
                if d["local_port"] > 0:
                    proxies.append(d)
            elif ptype == "httpconnect":
                # HTTPCONNECT 需要 local_port
                if d["local_port"] > 0:
                    proxies.append(d)

        return {
            "server_addr": self.server_addr_entry.get().strip(),
            "server_port": (
                int(self.server_port_entry.get().strip())
                if self.server_port_entry.get().strip().isdigit()
                else 7000
            ),
            "token": self.token_entry.get().strip(),
            "frpc_path": self.frpc_path_entry.get().strip() or "./frpc",
            "proxies": proxies,
        }

    def _save_config_ui(self):
        cfg = self._collect_config_from_ui()
        save_config(cfg)
        self.config_data = cfg
        self._append_log("[保存] 配置已保存到 " + CONFIG_FILE, "info")

    def _toggle_token(self):
        if self.token_entry.cget("show") == "•":
            self.token_entry.configure(show="")
            self.token_btn.configure(text="🔒")
        else:
            self.token_entry.configure(show="•")
            self.token_btn.configure(text="👁")

    # ==================== FRP 控制 ====================

    def start_frp(self):
        cfg = self._collect_config_from_ui()
        save_config(cfg)
        self.config_data = cfg

        # 更新 frpc 路径（自动补 .exe 后缀）
        frpc_path = cfg.get("frpc_path", "./frpc")
        if os.name == "nt" and not frpc_path.lower().endswith(".exe"):
            if os.path.exists(frpc_path + ".exe"):
                frpc_path += ".exe"
        self._frp_controller.frpc_path = frpc_path

        try:
            toml_path = generate_frpc_toml(cfg)
            self._append_log(
                f"[配置] 服务器 {cfg['server_addr']}:{cfg['server_port']}  |  "
                f"{len(cfg['proxies'])} 条映射",
                "info",
            )
            for p in cfg["proxies"]:
                ptype = p["type"].upper()
                if ptype in ("TCP", "UDP"):
                    detail = f":{p['local_port']} → :{p['remote_port']}"
                elif ptype in ("HTTP", "HTTPS"):
                    sub = p.get("subdomain", "")
                    domains = p.get("custom_domains", "")
                    if sub:
                        detail = f":{p['local_port']} → {sub} (子域名)"
                    elif domains:
                        first_domain = domains.split(",")[0].strip()
                        detail = f":{p['local_port']} → {first_domain}"
                    else:
                        detail = f":{p['local_port']}"
                elif ptype in ("STCP", "SUDP", "XTCP"):
                    detail = f":{p['local_port']} (密钥: {p.get('secret_key', '***')})"
                elif ptype == "TCPMUX":
                    route = p.get("route_rule", "")
                    detail = f":{p['local_port']}" + (f" → {route}" if route else "")
                elif ptype == "HTTPCONNECT":
                    detail = f":{p['local_port']}"
                else:
                    detail = f":{p['local_port']}"

                self._append_log(
                    f"       ↳ {p['name']}: {p['local_ip']}{detail}  [{ptype}]",
                    "info",
                )
        except Exception as e:
            self._append_log(f"[错误] 生成配置文件失败: {e}", "error")
            return

        self._frp_controller.start(toml_path)

    def stop_frp(self):
        self._frp_controller.stop()

    # ==================== 日志 ====================

    def _append_log(self, msg, level="info"):
        """带颜色标签的日志输出"""
        prefix_map = {
            "info":    ("", COLORS["text_secondary"]),
            "success": ("", COLORS["success"]),
            "warning": ("", COLORS["warning"]),
            "error":   ("", COLORS["danger"]),
        }
        color = prefix_map.get(level, ("", COLORS["text_secondary"]))[1]

        # 插入彩色文本（CTkTextbox 支持 tag）
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", msg + "\n", level)
            self.log_textbox.tag_config(level, foreground=color)
            self.log_textbox.see("end")
        except Exception:
            self.log_textbox.insert("end", msg + "\n")
            self.log_textbox.see("end")

    def _clear_log(self):
        self.log_textbox.delete("1.0", "end")

    # ==================== 状态轮询 ====================

    def _poll_status(self):
        running = self._frp_controller.is_running()
        if running:
            self.status_dot.configure(text_color=COLORS["success"])
            self.status_label.configure(
                text="运行中", text_color=COLORS["success"]
            )
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.status_dot.configure(text_color=COLORS["text_muted"])
            self.status_label.configure(
                text="未运行", text_color=COLORS["text_muted"]
            )
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
        self.after(2000, self._poll_status)

    # ==================== 窗口与退出 ====================

    def _minimize_to_tray(self):
        self.withdraw()

    def _full_exit(self):
        """完整退出：终止 frpc → 停托盘 → 销毁窗口"""
        self._frp_controller.force_kill()
        self.tray.stop()
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)


# ==================== 入口 ====================

if __name__ == "__main__":
    app = FRPGUI()
    app.mainloop()
