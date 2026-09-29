# -*- coding: utf-8 -*-
"""
监控网站一键发布脚本
把三个监控项目的 index.html 复制到本仓库(改名), 生成首页, git commit + push 到 GitHub Pages。
用法:
  python publish.py            # 正常发布
  python publish.py --check    # 只看将要发布什么, 不 commit 不 push
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (源目录, 目标文件名, 页面中文名, 简介)
PAGES = [
    (r'D:\AI research\hkex_di_monitor',    'di.html',        '披露权益监控', '自选股披露权益变动每日提示'),
    (r'D:\AI research\hkex_ann',           'ann.html',       '最新公告',     '自选股披露易最新公告'),
    (r'D:\AI research\southbound_monitor', 'southbound.html','南向资金看板', '17项指标+洋葱策略信号'),
]

# 首页标题/链接
SITE_NAME = '港股监控站'


def run(cmd, **kw):
    """跑 git 命令, 返回 (returncode, output)"""
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', shell=True, **kw)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def inject_noindex(path):
    """往页面 <head> 注入 noindex, 避免被搜索引擎收录(自选股数据不外泄到搜索结果)"""
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    tag = '<meta name="robots" content="noindex, nofollow">'
    if tag in html:
        return
    head = html.find('<head>')
    if head == -1:
        return
    at = head + len('<head>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html[:at] + '\n' + tag + html[at:])


def build_index():
    cards = []
    for src, fname, name, desc in PAGES:
        src_html = os.path.join(src, 'index.html')
        if not os.path.exists(src_html):
            print(f'!! 缺 {src_html}, 跳过该页')
            continue
        mtime = os.path.getmtime(src_html)
        import datetime
        ts = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        cards.append(f'''<a class="card" href="./{fname}">
  <div class="t">{name}</div>
  <div class="d">{desc}</div>
  <div class="m">更新于 {ts}</div>
</a>''')
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>''' + SITE_NAME + '''</title>
<style>
  body { font-family: system-ui, "Microsoft YaHei", sans-serif; background:#0f1419; color:#e6e6e6;
         margin:0; padding:40px 16px; }
  h1 { font-size:22px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; max-width:900px; }
  .card { display:block; background:#161b22; border:1px solid #30363d; border-radius:10px;
          padding:20px; text-decoration:none; color:inherit; transition:border-color .15s; }
  .card:hover { border-color:#58a6ff; }
  .t { font-size:17px; font-weight:600; margin-bottom:6px; }
  .d { font-size:13px; color:#8b949e; }
  .m { font-size:12px; color:#6e7681; margin-top:12px; }
  .foot { margin-top:32px; font-size:12px; color:#6e7681; max-width:900px; line-height:1.7; }
</style>
</head>
<body>
<h1>''' + SITE_NAME + '''</h1>
<div class="grid">
''' + '\n'.join(cards) + '''
</div>
<div class="foot">数据仅供个人研究使用, 不构成投资建议。每日 09:45 自动更新并发布。<br>
若某页显示旧数据, 大概率是当日抓取源休市/失败, 参考页面内更新时间。</div>
</body>
</html>'''
    with open(os.path.join(HERE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html 生成完毕')


def main():
    check_only = '--check' in sys.argv
    for src, fname, name, desc in PAGES:
        s = os.path.join(src, 'index.html')
        if os.path.exists(s):
            shutil.copyfile(s, os.path.join(HERE, fname))
            inject_noindex(os.path.join(HERE, fname))
            print(f'copied {name}: {s} -> {fname}')
        else:
            print(f'!! 缺源文件, 跳过: {s}')

    build_index()

    if check_only:
        print('\n[check 模式] 未 commit 未 push')
        return

    steps = [
        'git add -A',
        'git diff --cached --quiet && echo NOTHING_TO_COMMIT',
        'git commit -m "auto: update ' + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M') + '"',
        'git push origin main',
    ]
    for cmd in steps:
        rc, out = run(cmd)
        first = out.strip().splitlines()[0] if out.strip() else ''
        print(f'$ {cmd}\n  {first}')
        if 'NOTHING_TO_COMMIT' in out:
            print('无变更, 跳过 commit/push')
            return
        if rc != 0 and 'push' not in cmd:
            print(f'!! git 命令失败: {out[:300]}')
            sys.exit(1)
    print('发布完成')


if __name__ == '__main__':
    main()
