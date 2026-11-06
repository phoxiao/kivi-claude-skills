#!/usr/bin/env python3
"""按 assertion 给 ui-deslop 评测打分。用法：grade.py <iteration 目录> <原始 fixture>"""
import json, re, sys, pathlib

root = pathlib.Path(sys.argv[1])
fixture = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
evals_json = pathlib.Path(__file__).with_name("evals.json").read_text(encoding="utf-8")
DECLARED = {e["name"]: e["assertions"] for e in json.loads(evals_json)["evals"]}
SERVICES = "api-gateway|billing|search"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def read(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""


def visible(html):
    """去掉 style、script、注释，保留标签和文字。"""
    return re.sub(r"<(style|script)\b.*?</\1>|<!--.*?-->", "", html, flags=re.S | re.I)


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html)


def text_only(html):
    return re.sub(r"\s+", " ", strip_tags(visible(html))).strip()


def has(pat, s):
    return bool(re.search(pat, s, re.I | re.S))


def audit_fix(d):
    h = read(d / "slop-dashboard.html")
    v, t = visible(h), text_only(h)
    restart_named = len(re.findall(r'aria-label="[^"]*重启', v)) + len(
        re.findall(r">\s*重启\s*<", v)
    )
    has_data_rows = has(r"data-service|renderRow|services\s*=", h)
    def status_of(svc):
        """可见文字里，从 svc 到下一个服务名之间的片段。"""
        m = re.search(rf"{svc}(.*?)(?:{SERVICES}|\Z)", t, re.S)
        return m.group(1) if m else ""
    search_status = status_of("search")
    rows = re.findall(r"<(?:tr|li)\b.*?</(?:tr|li)>", v, re.S)
    same_row = any("重启" in r and "删除" in r for r in rows)
    ok_words = "正常|健康|ok|healthy|running|运行中"
    return [
        ("正常服务也有状态文字，不是空白", has(ok_words, status_of("api-gateway")) and has(ok_words, status_of("billing")), status_of("billing").strip()[:40]),
        ("删除按钮写全了动作和对象", has(r">\s*删除\s*billing\s*<", v)),
        ("删除按钮没有和重启按钮放在同一行", not same_row),
        ("删掉了 slogan", "一站式" not in t),
        ("删掉了「AI 驱动」徽章", "AI 驱动" not in t),
        ("标题里没有 emoji", not EMOJI.search(text_only(re.sub(r"<button\b.*?</button>", "", v, flags=re.S | re.I)))),
        ("删掉了模块说明文案", not has("这里展示|下方列出", t)),
        ("删掉了错误率和 P99 的定义说明", not has("是指失败请求|反映了最慢", t)),
        ("删掉了常态的「运行正常」", "运行正常" not in t),
        ("保留了错误率的时间范围", has(r"1\s*(小时|h)", t)),
        ("保留了延迟单位 ms", has(r"\bms\b", t)),
        ("保留了删除确认的影响范围", "无法恢复" in v and "告警规则" in v),
        ("search 的异常状态有文字，不只靠红点", has("异常|故障|不可用|宕机|down|error|失败|unhealthy", search_status), search_status[:80]),
        ("重启按钮有可访问名称（aria-label 或可见文字）", restart_named >= 3 or (has_data_rows and restart_named >= 1), f"{restart_named} 个"),
        ("拍平了卡片套卡片", not ('class="card"' in v and 'class="inner"' in v)),
    ]


def generate(d):
    h = read(d / "nodes.html")
    v = visible(h)
    outside = re.sub(r"<table\b.*?</table>", "", v, flags=re.S | re.I)
    outside_t = text_only(outside)
    return [
        ("生成了 nodes.html", bool(h)),
        ("没有做用户没要的 Drain 流程", "drain" not in h.lower()),
        ("没有做用户没要的详情抽屉或弹窗", not has(r"drawer|<dialog|aria-modal", h)),
        ("文件不超过 20KB", len(h.encode()) <= 20480, f"{len(h.encode())//1024} KB"),
        ("没有说明书式文案和 slogan", not has("这里展示|您可以|帮助您|一站式|智能|AI 驱动|实时掌握|轻松", text_only(h))),
        ("可见文字里没有 emoji", not EMOJI.search(outside_t)),
        ("没有渐变装饰", "gradient" not in h.lower()),
        ("用表格呈现节点", has(r"<table\b|role=\"table\"|el\(['\"]table|createElement\(['\"]table", h)),
        ("资源指标带单位", has(r"\d\s*(Gi|GiB|%)", h) or has(r"[\"'`]\s*(Gi|GiB|%)", h)),
        ("异常节点用文字标出", "NotReady" in h),
        ("表格外的静态文字不超过 200 字符", len(outside_t) <= 200, f"{len(outside_t)} 字符"),
    ]


def install(d):
    a = read(d / "AGENTS.md")
    ui_heads = [l for l in a.splitlines() if re.match(r"^#{1,6}\s*UI\b", l)]
    return [
        ("规则限制了副标题和说明文案", has("secondary label|subtitle|副标题", a)),
        ("规则覆盖了错误和空状态", has("error|错误", a) and has("empty|空状态", a)),
        ("只有一个 UI 小节，没有重复追加", len(ui_heads) == 1, f"{ui_heads}"),
        ("保留了 Element Plus 规则", "Element Plus" in a and "do not add new UI libraries" in a.replace("Do not", "do not")),
        ("保留了 Stack 和 Testing 小节", "snake_case" in a and "pnpm test" in a),
        ("没有混入与 UI 无关的工作方式规则", not has("first principles|第一性原理|HANDOFF", a)),
        ("要求与现有界面保持一致", has("existing screen|现有界面|已有界面|existing (page|UI|product pattern)", a)),
    ]


def audit_only(d):
    h = read(d / "slop-dashboard.html")
    r = read(d / "report.md")
    m = re.search(r"##[^\n]*(留|不能砍|别砍|不要砍|不要动).*?(?=\n## |\Z)", r, re.S)
    keep = m.group(0) if m else ""
    extra = [p.name for p in d.iterdir() if p.name not in ("slop-dashboard.html", "report.md")]
    return [
        ("没有改动 HTML", h == fixture),
        ("没有新建其他文件", not extra, str(extra)),
        ("列出了 slogan、AI 徽章、运行正常", all(k in r for k in ("一站式", "AI 驱动", "运行正常"))),
        ("「运行正常」建议缩短而不是留空", has(r"运行正常.{0,120}(缩|短|改成|「正常」|`正常`|\|\s*正常)", r)),
        ("指出时间范围要留", has(r"近\s*1\s*小时", keep)),
        ("指出单位 ms 要留", has(r"\bms\b", keep)),
        ("指出删除确认要留", has(r"删除确认|无法恢复", keep)),
        ("指出 search 异常只有红点、缺文字", has(r"search.{0,160}(红点|颜色|文字|状态)|(红点|只靠颜色).{0,160}search", r)),
    ]


CASES = {
    "audit-and-fix": audit_fix,
    "generate-from-scratch": generate,
    "install-rules": install,
    "audit-only-keeps-essentials": audit_only,
}

table = {}
for name, fn in CASES.items():
    for cfg in ("with_skill", "without_skill"):
        run = root / name / cfg
        res = fn(run / "outputs")
        if [t for t, *_ in res] != DECLARED[name]:
            sys.exit(f"{name}: grade.py 与 evals.json 的断言文字不一致")
        exp = [{"text": t, "passed": bool(p), "evidence": e[0] if e else ""} for t, p, *e in res]
        passed = sum(x["passed"] for x in exp)
        (run / "grading.json").write_text(json.dumps({
            "expectations": exp,
            "summary": {"passed": passed, "failed": len(exp) - passed, "total": len(exp), "pass_rate": round(passed / len(exp), 2)},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        table.setdefault(name, {})[cfg] = exp
    meta_path = root / name / "eval_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["assertions"] = [x["text"] for x in table[name]["with_skill"]]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

for name, cfgs in table.items():
    w, b = cfgs["with_skill"], cfgs["without_skill"]
    print(f"\n## {name}: 带 skill {sum(x['passed'] for x in w)}/{len(w)}，对照 {sum(x['passed'] for x in b)}/{len(b)}")
    for x, y in zip(w, b):
        print(f"  {'Y' if x['passed'] else 'N'} {'Y' if y['passed'] else 'N'}  {x['text']}  {x['evidence'] or ''} | {y['evidence'] or ''}")
