# -*- coding: utf-8 -*-
"""
push_reconcile.py — 推送对账补推循环(计划任务 MonitorSite_Push_Reconcile 每10分钟跑一次,
工作日 08:15-12:15). 三件事, 全部幂等:
  1) git push: rc==0 即视为OK(含"already up-to-date"), 未推上去的提交在此补推
  2) 恢复通知: 当日某波存在 _push.fail 且本轮 push 成功 -> 发一条"补推成功"通知(每波每天最多1条)
  3) 摘要补发: 当日某波存在 _text.txt 但无 _sent.ok -> 原文重发摘要
状态文件由 push_site.py 写入: state/wave_YYYYMMDD_{1|2}_{_text.txt|_sent.ok|_push.ok|_push.fail|_recovered.ok}
守卫: push_site.log 3分钟内有改动 = 正有一波在跑, 本轮直接退出(避免与其内部重试互相干扰)
"""
import datetime
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, 'state')
LOG = os.path.join(STATE, 'reconcile.log')

sys.path.insert(0, r'D:\AI research\southbound_monitor')
import push_feishu as bridge  # noqa: E402

SITE_URL = 'https://benedetti117.github.io/hk-monitor/'


def log(msg):
    ts = datetime.datetime.now().strftime('%m-%d %H:%M:%S')
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] {msg}\n')
    # 日志超500行截到400行
    try:
        with open(LOG, encoding='utf-8') as f:
            lines = f.readlines()
        if len(lines) > 500:
            with open(LOG, 'w', encoding='utf-8') as f:
                f.writelines(lines[-400:])
    except OSError:
        pass


def run(cmd):
    # 2026-10-27: 改为无shell直跑(列表参数)。此前 shell=True 下超时只能杀掉 cmd.exe,
    # 被网络卡住的 git.exe 成为孤儿并握住管道, 子进程迟迟不返回 -> 一轮可远超10分钟,
    # 被 ExecutionTimeLimit 强杀(rc=267014)且不留日志, 且 IgnoreNew 会把后续 tick 全堵住
    # (10-27 晨 08:15-09:40 九个 tick 全缺即此症状)。直跑时超时杀的就是 git.exe 本体。
    try:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                           timeout=90)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, 'timeout after 90s'


def wave_in_flight():
    """push_site.log 180秒内被写过 = 一波推送正在跑"""
    p = os.path.join(HERE, 'push_site.log')
    if not os.path.exists(p):
        return False
    return time.time() - os.path.getmtime(p) < 180


def sf(wave, suffix):
    day = datetime.datetime.now().strftime('%Y%m%d')
    return os.path.join(STATE, f'wave_{day}_{wave}{suffix}')


def send(text):
    ok, out = bridge.run_lark(['im', '+messages-send', '--as', 'bot',
                               '--user-id', bridge.RECIPIENT_OU,
                               '--text', text])
    return ok


def cleanup_old(days=3):
    """清掉3天前的状态文件(防目录膨胀)"""
    cut = time.time() - days * 86400
    for fn in os.listdir(STATE):
        if not fn.startswith('wave_'):
            continue
        p = os.path.join(STATE, fn)
        try:
            if os.path.getmtime(p) < cut:
                os.remove(p)
        except OSError:
            pass


def main():
    os.makedirs(STATE, exist_ok=True)
    if wave_in_flight():
        log('wave in flight, skip')
        return 0
    cleanup_old()

    # 1) 补推(2次尝试, 间隔15s; rc==0 含 up-to-date)
    push_ok = False
    for attempt in (1, 2):
        rc, out = run(['git', 'push', 'origin', 'main'])
        first = out.strip().splitlines()[0] if out.strip() else 'ok'
        log(f'push try{attempt} rc={rc}: {first[:120]}')
        if rc == 0:
            push_ok = True
            break
        if attempt == 1:
            time.sleep(15)

    if not push_ok:
        log('round done (push still failing, next tick retries)')
        return 0

    # 2) 恢复通知: 曾失败(push.fail) 且 本轮push成功 -> 一次性告知
    hhmm = datetime.datetime.now().strftime('%H:%M')
    for w in ('1', '2'):
        if os.path.exists(sf(w, '_push.fail')) and not os.path.exists(sf(w, '_recovered.ok')):
            if send(f'✅ 监控站补推成功({hhmm}), 线上已恢复最新, 请刷新查看\n{SITE_URL}'):
                open(sf(w, '_recovered.ok'), 'w').close()
                log(f'wave {w}: recovery notice sent')

    # 3) 摘要补发: 有原文(_text.txt)但无 _sent.ok -> 原文重发
    for w in ('1', '2'):
        tp, sp = sf(w, '_text.txt'), sf(w, '_sent.ok')
        if os.path.exists(tp) and not os.path.exists(sp):
            with open(tp, encoding='utf-8') as f:
                text = f.read()
            if send(text):
                open(sp, 'w').close()
                log(f'wave {w}: summary resent')

    log('round ok')
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
