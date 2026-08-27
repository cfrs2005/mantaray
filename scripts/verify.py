#!/usr/bin/env python3
"""Mantaray 配置门禁。

守住三件靠人记必然出错的事：
  1. [Host] 的三个语法坑（空格 / 通配不覆盖裸域 / 顺序敏感）
  2. DNS 铁律：绑定解析源的域名，出口必须是 DIRECT
  3. configs/*.conf 与 dns/pinning.conf 不漂移

    python3 scripts/verify.py           # 离线，全部静态断言
    python3 scripts/verify.py --live    # 追加：RULE-SET 可达性 + 实测解析对照
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICIES = {"DIRECT", "PROXY", "REJECT", "REJECT-TINYGIF"}
HOST_RE = re.compile(r"^(?P<dom>[^\s=]+)\s*=\s*(?P<val>.+?)\s*$")
DOMAIN_RE = re.compile(r"^\*?[\w.-]+$")
TOKEN_RE = re.compile(r"^(\*?[\w.-]+|[\d.]+/\d+|[\da-fA-F:]+/\d+)$")


class Report:
    def __init__(self):
        self.fail, self.warn, self.ok = [], [], 0

    def check(self, cond, where, msg):
        if cond:
            self.ok += 1
        else:
            self.fail.append(f"{where}: {msg}")

    def note(self, cond, where, msg):
        if cond:
            self.ok += 1
        else:
            self.warn.append(f"{where}: {msg}")

    @staticmethod
    def _fold(items):
        """同一条消息出现在多个 conf 里合成一行，避免 4 份产物刷屏。"""
        groups = {}
        for it in items:
            where, msg = it.split(": ", 1)
            groups.setdefault(msg, []).append(where)
        return [(msg, wheres) for msg, wheres in groups.items()]

    def done(self):
        for msg, wheres in self._fold(self.warn):
            print(f"  WARN  {msg}  [{len(wheres)} conf]" if len(wheres) > 1 else f"  WARN  {wheres[0]}: {msg}")
        for msg, wheres in self._fold(self.fail):
            print(f"  FAIL  {msg}  [{len(wheres)} conf]" if len(wheres) > 1 else f"  FAIL  {wheres[0]}: {msg}")
        print(f"\n{self.ok} passed, {len(self.warn)} warnings, {len(self.fail)} failures")
        return 1 if self.fail else 0


def parse(text):
    """把 conf 切成 general(dict) / rules(list) / hosts(list)。注释与空行丢弃。"""
    out = {"general": {}, "rules": [], "hosts": []}
    section, pending = None, []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            section, pending = line.strip("[]").lower(), []
            continue
        if not line:
            pending = []
            continue
        if line.startswith("#"):
            pending.append(line)
            continue
        if section == "general" and "=" in line:
            k, v = line.split("=", 1)
            out["general"][k.strip()] = v.strip()
        elif section == "rule":
            out["rules"].append(line)
        elif section == "host":
            out["hosts"].append((line, any("pin-exempt" in c for c in pending)))
    return out


def rule_parts(line):
    """DOMAIN-SUFFIX,a.com,PROXY,extended-matching -> (type, value, policy)"""
    p = [x.strip() for x in line.split(",")]
    if p[0] == "FINAL":
        return "FINAL", "", p[1] if len(p) > 1 else ""
    return (p[0], p[1] if len(p) > 1 else "", p[2] if len(p) > 2 else "")


def domain_policy(rules, domain):
    """按 Shadowrocket 的先命中先生效，算出一个域名实际落到哪个策略。"""
    bare = domain.lstrip("*.")
    for line in rules:
        kind, val, pol = rule_parts(line)
        if kind == "DOMAIN" and val == bare:
            return pol
        if kind == "DOMAIN-SUFFIX" and (bare == val or bare.endswith("." + val)):
            return pol
        if kind == "DOMAIN-KEYWORD" and val in bare:
            return pol
    return None


def check_general(conf, name, rep):
    g = conf["general"]
    for key in ("skip-proxy", "bypass-tun"):
        for tok in (t.strip() for t in g.get(key, "").split(",")):
            if not tok:
                continue
            rep.check(bool(TOKEN_RE.match(tok)), name, f"{key} 含非法 token {tok!r}")
    for key in ("dns-fallback-system", "dns-direct-system"):
        if key in g and "strict" in name:
            rep.check(g[key] == "false", name, f"严格模式下 {key} 必须为 false，破坏解析一致性")
    if "dns-server" in g:
        rep.check(bool(g["dns-server"].strip()), name, "dns-server 为空")


def check_host_syntax(conf, name, rep):
    seen = {}
    for line, _ in conf["hosts"]:
        m = HOST_RE.match(line)
        rep.check(bool(m), name, f"[Host] 语法错误: {line!r}")
        if not m:
            continue
        dom, val = m.group("dom"), m.group("val")
        rep.check(bool(DOMAIN_RE.match(dom)), name, f"[Host] 域名含非法字符（多半是多打了空格）: {dom!r}")
        rep.check(dom not in seen, name, f"[Host] 域名重复定义: {dom}")
        seen[dom] = val
        rep.check(
            val.startswith("server:") or re.match(r"^[\d.]+$|^[\da-fA-F:]+$|^[\w.-]+$", val),
            name, f"[Host] 取值形态不认识: {dom} = {val}")
    for dom in seen:
        if dom.startswith("*."):
            rep.note(dom[2:] in seen, name,
                     f"[Host] {dom} 没有配套的裸域条目 {dom[2:]}（通配不匹配裸域）")


def check_host_order(conf, name, rep):
    """具体域名必须写在同域通配之前，否则被通配抢先，静默失效。"""
    wildcards = []
    for line, _ in conf["hosts"]:
        m = HOST_RE.match(line)
        if not m:
            continue
        dom = m.group("dom")
        if dom.startswith("*."):
            wildcards.append(dom)
            continue
        shadow = [w for w in wildcards if dom.endswith(w[1:])]
        rep.check(not shadow, name,
                  f"[Host] {dom} 被前面的 {shadow[0] if shadow else ''} 抢先匹配，需上移")


def check_pin_pairing(conf, name, rep):
    """DNS 铁律：绑了解析源的域名，出口必须是 DIRECT；PROXY 域名不得出现在 [Host]。"""
    for line, exempt in conf["hosts"]:
        m = HOST_RE.match(line)
        if not m or exempt:
            continue
        dom = m.group("dom")
        pol = domain_policy(conf["rules"], dom)
        rep.check(pol != "PROXY", name,
                  f"[Host] 给 PROXY 域名 {dom} 绑了本地解析 —— 国内 IP 走海外出口，必须删掉这条")
        rep.note(pol == "DIRECT", name,
                 f"[Host] {dom} 绑了解析源但没有显式 DIRECT 规则，出口由 GEOIP 兜底、不确定")
    for dom in (t.strip() for t in conf["general"].get("always-real-ip", "").split(",")):
        if not dom:
            continue
        rep.check(domain_policy(conf["rules"], dom) != "PROXY", name,
                  f"always-real-ip 含 PROXY 域名 {dom} —— 会强制本地解析，破坏落地解析")


def check_rules(conf, name, rep):
    seen, wildcards = {}, []
    for line in conf["rules"]:
        kind, val, pol = rule_parts(line)
        if kind == "FINAL":
            continue
        if kind.startswith("RULE-SET") or kind == "GEOIP":
            continue
        rep.check(pol in POLICIES or not pol.isupper(), name, f"未知策略 {pol!r}: {line}")
        key = (kind, val)
        rep.check(key not in seen, name, f"规则重复: {kind},{val}（已在上方声明为 {seen.get(key)}）")
        seen[key] = pol
        if kind == "DOMAIN-SUFFIX":
            shadow = [w for w, wp in wildcards if val.endswith("." + w) and wp != pol]
            rep.check(not shadow, name,
                      f"{val} 被前面的 DOMAIN-SUFFIX,{shadow[0] if shadow else ''} 抢先，需上移")
            wildcards.append((val, pol))
    finals = [l for l in conf["rules"] if l.startswith("FINAL")]
    rep.check(len(finals) == 1, name, f"FINAL 应恰好一条，实际 {len(finals)} 条")
    if finals:
        rep.check(conf["rules"][-1] == finals[0], name, "FINAL 必须是 [Rule] 段最后一条")


def private_tokens():
    """从私有层抽出域名与 IP —— 这些一个字都不该出现在公开 conf 里。"""
    src = ROOT / "dns" / "pinning.local.conf"
    if not src.exists():
        return set()
    out = set()
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("#").strip()
        m = HOST_RE.match(line)
        if m and not m.group("dom").startswith("["):
            out.add(m.group("dom").lstrip("*."))
            val = m.group("val")
            if not val.startswith("server:"):
                out.add(val)
        kind, val, _ = rule_parts(line) if "," in line else ("", "", "")
        if kind.startswith("DOMAIN") or kind.startswith("IP-CIDR"):
            out.add(val.split("/")[0])
        if kind in ("bypass-tun", "skip-proxy"):
            continue
    return {t for t in out if t and "." in t and not t.startswith("doh.")}


def check_no_leak(rep):
    """私有层内容漏进公开 conf —— sync 的 GENERAL 覆盖是单向的，最容易在这里出事。"""
    tokens = private_tokens()
    if not tokens:
        return
    for path in sorted((ROOT / "configs").glob("*.conf")):
        text = path.read_text(encoding="utf-8")
        hit = sorted(t for t in tokens if t in text)
        rep.check(not hit, str(path.relative_to(ROOT)),
                  f"私有层内容漏进公开配置: {', '.join(hit[:4])}{' …' if len(hit) > 4 else ''}")


def check_sync(rep):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync.py"), "--check"],
                       capture_output=True, text=True)
    rep.check(r.returncode == 0, "sync", r.stdout.strip() or "configs/ 与 dns/pinning.conf 漂移")


def resolve(domain):
    url = f"https://doh.pub/dns-query?name={domain}&type=A"
    req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.load(r)
    return [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]


def check_live(conf, name, rep):
    for line in conf["rules"]:
        if not line.startswith("RULE-SET"):
            continue
        url = line.split(",")[1]
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                rep.check(r.status == 200, name, f"RULE-SET 不可达 {url}")
        except Exception as e:
            rep.check(False, name, f"RULE-SET 不可达 {url} ({e})")
    for line, _ in conf["hosts"]:
        m = HOST_RE.match(line)
        if not m or not m.group("val").startswith("server:"):
            continue
        dom = m.group("dom").lstrip("*.")
        try:
            ips = resolve(dom)
        except Exception as e:
            rep.note(False, name, f"实测解析失败 {dom} ({e})")
            continue
        rep.note(bool(ips), name, f"实测解析为空 {dom} —— 绑定的 DNS 源可能不认这个域名")


def main():
    live = "--live" in sys.argv[1:]
    rep = Report()
    check_sync(rep)
    check_no_leak(rep)
    targets = sorted((ROOT / "configs").glob("*.conf"))
    targets += sorted((ROOT / "configs" / "local").glob("*.conf"))
    for path in targets:
        name = str(path.relative_to(ROOT))
        conf = parse(path.read_text(encoding="utf-8"))
        check_general(conf, name, rep)
        check_host_syntax(conf, name, rep)
        check_host_order(conf, name, rep)
        check_pin_pairing(conf, name, rep)
        check_rules(conf, name, rep)
        if live:
            check_live(conf, name, rep)
    print(f"checked {len(targets)} config(s){' + live' if live else ''}")
    return rep.done()


if __name__ == "__main__":
    sys.exit(main())
