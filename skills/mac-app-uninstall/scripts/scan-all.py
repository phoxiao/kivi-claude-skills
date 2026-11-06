#!/usr/bin/env python3
"""
扫描所有已安装应用，产出 JSON 快照，供 build-ui.sh 生成筛选界面。

    用法: scan-all.py [输出路径]        默认 ./apps.json

只读。为每个应用给出本体大小、残留大小与路径、闲置天数、属主、是否运行、
有无开机代理（含 KeepAlive 标记）、是否 Setapp 托管。

性能说明（这是重写的原因）：第一版按「每个应用 × 每个位置」各跑一次 du，
把 ~/Library/Containers 这种目录重复遍历了几十遍，微信那个 6G 容器被反复扫，
50 个应用要跑十几分钟。现在每个基础目录只 du 一遍建成索引，再在内存里匹配，
总耗时约等于 du 一次 ~/Library。
"""
import json, os, re, subprocess, sys, time

HOME = os.path.expanduser("~")
OUT = sys.argv[1] if len(sys.argv) > 1 else "./apps.json"

BASES = [f"{HOME}/Library/Application Support", f"{HOME}/Library/Containers",
         f"{HOME}/Library/Group Containers", f"{HOME}/Library/Caches",
         f"{HOME}/Library/Preferences", f"{HOME}/Library/Preferences/ByHost",
         f"{HOME}/Library/Saved Application State", f"{HOME}/Library/HTTPStorages",
         f"{HOME}/Library/WebKit", f"{HOME}/Library/Logs",
         f"{HOME}/Library/Application Scripts"]
AGENT_DIRS = [f"{HOME}/Library/LaunchAgents", "/Library/LaunchAgents",
              "/Library/LaunchDaemons", "/Library/PrivilegedHelperTools"]
APP_DIRS = ["/Applications", "/Applications/Setapp", f"{HOME}/Applications"]


def du_index(directory):
    """对一个目录下的直接子项做一次 du，返回 {路径: MB}。"""
    if not os.path.isdir(directory):
        return {}
    try:
        entries = [os.path.join(directory, e) for e in os.listdir(directory)]
    except OSError:
        return {}
    if not entries:
        return {}
    out = {}
    # 分批调用，避免超出 ARG_MAX
    for i in range(0, len(entries), 200):
        chunk = entries[i:i + 200]
        try:
            r = subprocess.run(["du", "-sm", *chunk],
                               capture_output=True, text=True, timeout=600)
        except (subprocess.TimeoutExpired, OSError):
            continue
        for line in r.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                try:
                    out[parts[1]] = int(parts[0])
                except ValueError:
                    pass
    return out


def belongs(name, bid, disp):
    """判断一个文件名是否属于该应用。与 audit-app.sh 的 belongs() 语义一致。

    刻意不做模糊子串：com.termius-dmg.mac 的末段是 'mac'，子串匹配会命中
    CleanMyMac 的特权助手和几十个系统扩展。第一版真出过这个 bug。
    """
    base = name.rsplit(".", 1)[0] if "." in name else name
    if bid:
        if name == bid or base == bid:
            return True
        if name.startswith(bid + ".") or name.endswith("." + bid) or base.endswith("." + bid):
            return True
    if disp and len(disp) >= 4:
        if name == disp or base == disp:
            return True
        if name.startswith(disp + ".") or name.startswith(disp + "-"):
            return True
        # group container 的标识符常和 bundle id 完全不同：
        # OrbStack 的 bundle id 是 dev.kdrag0n.MacVirt，group container 却叫
        # HUAQ24HBR6.dev.orbstack。比的是整段相等，不是子串。
        if name.lower().rsplit(".", 1)[-1] == disp.lower().replace(" ", ""):
            return True
    return False


def bundle_id(app):
    try:
        r = subprocess.run(["plutil", "-extract", "CFBundleIdentifier", "raw",
                            os.path.join(app, "Contents/Info.plist")],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def last_used(app):
    try:
        r = subprocess.run(["mdls", "-name", "kMDItemLastUsedDate", "-raw", app],
                           capture_output=True, text=True, timeout=10)
        v = r.stdout.strip()
        return "" if v in ("", "(null)") else v.split(" ")[0]
    except (subprocess.TimeoutExpired, OSError):
        return ""


def main():
    t0 = time.time()
    print("建立目录索引…", file=sys.stderr)
    index = {}          # 基础目录 -> {路径: MB}
    for b in BASES:
        index[b] = du_index(b)
    agent_names = {}    # 目录 -> [文件名]
    for d in AGENT_DIRS:
        try:
            agent_names[d] = os.listdir(d)
        except OSError:
            agent_names[d] = []

    print("扫描应用…", file=sys.stderr)
    app_sizes = {}
    for d in APP_DIRS:
        app_sizes.update({p: mb for p, mb in du_index(d).items() if p.endswith(".app")})

    running = subprocess.run(["ps", "-Axo", "command"], capture_output=True, text=True).stdout

    apps, now = [], time.time()
    for app in sorted(app_sizes):
        disp = os.path.basename(app)[:-4]
        bid = bundle_id(app)
        paths, res_mb, newest = [], 0, 0
        for b, idx in index.items():
            for p, mb in idx.items():
                if not belongs(os.path.basename(p), bid, disp):
                    continue
                res_mb += mb
                try:
                    m = os.stat(p).st_mtime
                    newest = max(newest, m)
                except OSError:
                    pass
                paths.append({"p": p.replace(HOME, "~", 1), "mb": mb})
        if len(disp) >= 4:
            low = disp.lower().replace(" ", "")
            for p in (f"{HOME}/.{low}", f"{HOME}/.config/{low}"):
                if os.path.exists(p):
                    mb = du_index(os.path.dirname(p)).get(p, 0)
                    res_mb += mb
                    paths.append({"p": p.replace(HOME, "~", 1), "mb": mb})

        agents, keepalive = [], False
        for d, names in agent_names.items():
            for n in names:
                if not belongs(n, bid, disp):
                    continue
                f = os.path.join(d, n)
                agents.append(f.replace(HOME, "~", 1))
                try:
                    with open(f, "rb") as fh:
                        if b"KeepAlive" in fh.read():
                            keepalive = True
                except OSError:
                    pass

        lu = last_used(app)
        idle = -1
        if newest:
            idle = int((now - newest) // 86400)
        elif lu:
            try:
                idle = int((now - time.mktime(time.strptime(lu, "%Y-%m-%d"))) // 86400)
            except ValueError:
                pass

        try:
            owner = subprocess.run(["stat", "-f", "%Su", app], capture_output=True,
                                   text=True, timeout=10).stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            owner = ""

        app_mb = app_sizes[app]
        apps.append({
            "name": disp, "path": app, "bid": bid,
            "app_mb": app_mb, "res_mb": res_mb, "total_mb": app_mb + res_mb,
            "owner": owner, "running": app in running,
            "setapp": app.startswith("/Applications/Setapp/"),
            "last_used": lu, "idle_days": idle,
            "keepalive": keepalive, "agents": agents,
            "paths": sorted(paths, key=lambda x: -x["mb"]),
        })

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%d %H:%M"),
                   "host": subprocess.run(["scutil", "--get", "ComputerName"],
                                          capture_output=True, text=True).stdout.strip(),
                   "apps": apps}, f, ensure_ascii=False)
    print(f"已写入 {OUT}（{len(apps)} 个应用，耗时 {time.time()-t0:.0f}s）", file=sys.stderr)


if __name__ == "__main__":
    main()
