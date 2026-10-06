# -*- coding: utf-8 -*-
"""
监控站统一推送: build + 推飞书 + (有远端时)发布线上
每天2次: wave1=07:50复盘完成后(6页齐), wave2=09:35回购完成后(补回购tab)
推送: 发1条文字摘要(内含线上站直达链接, 飞书不能预览html附件, 文件推送已弃用);
线上版为 iframe 多文件结构(index.html), 两者由同一次 build 产出。
用法:
  python push_site.py 1      # wave1
  python push_site.py 2      # wave2
  python push_site.py 1 --dry  # 只打印摘要不发
"""
import os
import subprocess
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ---- 飞书桥接(复用南向 monitor 的实现, 凭证/收件人一致) ----
sys.path.insert(0, r'D:\AI research\southbound_monitor')
import push_feishu as bridge  # noqa: E402  (run_lark, RECIPIENT_OU)

import publish  # noqa: E402  (PAGES, build_index 需要)


def stat_page(src, sname):
    """(tab名, 源文件mtime -> 'MM-DD HH:MM') 供摘要展示各tab新鲜度"""
    p = os.path.join(src, sname)
    if not os.path.exists(p):
        return None
    return datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%m-%d %H:%M')


def build_wave(wave):
    """重建监控站页面 + 组装摘要文字"""
    # 1) 拷贝+重建(不碰git)
    import shutil
    lines = []
    for src, sname, fname, name, desc, variant in publish.PAGES:
        s = os.path.join(src, sname)
        if not os.path.exists(s):
            lines.append(f'{name}: 缺源文件')
            continue
        import shutil as sh
        sh.copyfile(s, os.path.join(HERE, fname))
        publish.inject_noindex(os.path.join(HERE, fname))
        if variant:
            publish.apply_ann_variant(os.path.join(HERE, fname), variant)
        lines.append(f'{name}: {stat_page(src, sname)}')
    publish.build_index()
    publish.build_offline()   # 离线单文件版(供飞书推送下载)
    return lines


SITE_URL = 'https://benedetti117.github.io/hk-monitor/'


def wave_text(wave, lines):
    tag = '🟦 早间版' if wave == 1 else '🟧 回购更新版'
    now = datetime.datetime.now().strftime('%H:%M')
    return (f'🖥️ 监控站 {tag} {now}\n'
            + '\n'.join(lines)
            + f'\n\n🔗 {SITE_URL}')


def push_feishu_index(title_note=''):
    """(已弃用文件推送) 飞书不能预览html附件, 改为摘要内带线上链接, 本函数保留占位"""
    return True


def git_publish():
    """git commit + push(未配远端时静默跳过)"""
    rc, out = publish.run('git remote get-url origin')
    if rc != 0:
        print('(未配置 GitHub 远端, 跳过线上发布)')
        return True
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    for cmd in ('git add -A',
                'git commit -m "auto: update ' + ts + '"'):
        rc, out = publish.run(cmd)
        print(f'$ {cmd} -> {out.strip().splitlines()[0] if out.strip() else "ok"}')
    # push 网络易抖, 重试3次
    import time
    for attempt in range(3):
        rc, out = publish.run('git push origin main')
        print(f'$ git push origin main -> {out.strip().splitlines()[0] if out.strip() else "ok"}')
        if rc == 0:
            break
        time.sleep(10)
    return rc == 0


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    wave = 1
    for a in sys.argv[1:]:
        if a in ('1', '2'):
            wave = int(a)
    dry = '--dry' in sys.argv

    lines = build_wave(wave)
    text = wave_text(wave, lines)
    print('=' * 40)
    print(text)
    print('=' * 40)
    if dry:
        print('(dry 模式, 不推送不发布)')
        return 0

    ok1, out1 = bridge.run_lark(['im', '+messages-send', '--as', 'bot',
                                 '--user-id', bridge.RECIPIENT_OU,
                                 '--text', text])
    print('摘要推送:', 'OK' if ok1 else out1)
    ok2 = push_feishu_index()   # 占位恒True(文件推送已弃用, 摘要内已带链接)
    ok3 = git_publish()
    return 0 if (ok1 and ok2) else 1


if __name__ == '__main__':
    sys.exit(main())
