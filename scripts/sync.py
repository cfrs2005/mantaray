#!/usr/bin/env python3
"""把 dns/pinning*.conf 的绑定块注入 configs/*.conf。

[Host] 段不支持 RULE-SET 远程加载，只能内联进每个 conf。这个脚本让
「域名 -> (解析源, 流量出口)」这张表只有一份真源，4 个 conf 是产物。

    python3 scripts/sync.py            # 公开层 -> configs/，公开层+私有层 -> configs/local/
    python3 scripts/sync.py --public   # 只生成 configs/
    python3 scripts/sync.py --check    # 只检查漂移，不写文件（CI/verify 用）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_SRC = ROOT / "dns" / "pinning.conf"
LOCAL_SRC = ROOT / "dns" / "pinning.local.conf"
CONFS = ["main.conf", "daily.conf", "strict.conf", "debug.conf"]
KINDS = ("GENERAL", "RULE", "HOST")


def extract(text, kind):
    """取出一个标记块的内容行（不含标记本身）。块不存在返回空列表。"""
    pat = rf"^# ==== MANTARAY-PINNING-{kind}-BEGIN ====$(.*?)^# ==== MANTARAY-PINNING-{kind}-END ====$"
    m = re.search(pat, text, re.S | re.M)
    return m.group(1).strip("\n").splitlines() if m else []


def inject(conf, kind, lines):
    """用 lines 替换 conf 里对应标记块的内容。标记块不存在则原样返回。"""
    begin = f"# ==== MANTARAY-PINNING-{kind}-BEGIN ===="
    end = f"# ==== MANTARAY-PINNING-{kind}-END ===="
    body = "\n".join(lines)
    payload = f"{begin}\n{body}\n{end}" if body else f"{begin}\n{end}"
    pat = rf"^{re.escape(begin)}$.*?^{re.escape(end)}$"
    return re.sub(pat, lambda _: payload, conf, count=1, flags=re.S | re.M)


def apply_general(conf, lines):
    """[General] 里同名 key 整行替换，不存在则追加到段末。"""
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key = line.split("=", 1)[0].strip()
        pat = rf"^{re.escape(key)}\s*=.*$"
        if re.search(pat, conf, re.M):
            conf = re.sub(pat, lambda _: line, conf, count=1, flags=re.M)
        else:
            conf = re.sub(r"(\n)(\[Rule\])", rf"{line}\1\1\2", conf, count=1)
    return conf


def build(conf_text, blocks):
    conf_text = apply_general(conf_text, blocks["GENERAL"])
    for kind in ("RULE", "HOST"):
        conf_text = inject(conf_text, kind, blocks[kind])
    return conf_text


def load_blocks(*sources):
    """按顺序合并多个真源的同名块；后面的追加在前面之后。"""
    blocks = {k: [] for k in KINDS}
    for path in sources:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for kind in KINDS:
            got = extract(text, kind)
            if not got:
                continue
            if blocks[kind]:
                blocks[kind].append("")
            blocks[kind].extend(got)
    return blocks


def main():
    args = set(sys.argv[1:])
    check_only = "--check" in args
    public_only = "--public" in args

    public = load_blocks(PUBLIC_SRC)
    drift = []

    for name in CONFS:
        path = ROOT / "configs" / name
        src = path.read_text(encoding="utf-8")
        out = build(src, public)
        if out != src:
            drift.append(name)
            if not check_only:
                path.write_text(out, encoding="utf-8")

    if check_only:
        if drift:
            print("DRIFT: configs/ 与 dns/pinning.conf 不一致 -> " + ", ".join(drift))
            return 1
        print("OK: configs/ 与 dns/pinning.conf 一致")
        return 0

    print(f"public -> configs/  ({len(public['RULE'])} rule / {len(public['HOST'])} host 行)")

    if public_only or not LOCAL_SRC.exists():
        if not LOCAL_SRC.exists() and not public_only:
            print(f"skip local: {LOCAL_SRC.name} 不存在（可从 pinning.local.example.conf 复制）")
        return 0

    merged = load_blocks(PUBLIC_SRC, LOCAL_SRC)
    outdir = ROOT / "configs" / "local"
    outdir.mkdir(exist_ok=True)
    for name in CONFS:
        src = (ROOT / "configs" / name).read_text(encoding="utf-8")
        (outdir / name).write_text(build(src, merged), encoding="utf-8")
    print(f"public+local -> configs/local/  ({len(merged['RULE'])} rule / {len(merged['HOST'])} host 行)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
