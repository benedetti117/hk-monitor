# -*- coding: utf-8 -*-
"""
监控网站一键发布脚本
把三个监控项目的 index.html 复制到本仓库(改名, 注入noindex),
生成合并版首页(顶部tab切换 + iframe懒加载), git commit + push 到 GitHub Pages。
用法:
  python publish.py            # 正常发布
  python publish.py --check    # 只本地生成文件, 不 commit 不 push
"""
import os
import shutil
import subprocess
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

# (源目录, 源文件名, 目标文件名, 页面中文名, 简介) — 顺序即tab顺序, 第一项为默认首页
PAGES = [
    (r'D:\AI research\每日复盘\input',     'review.html',    'review.html',  '每日复盘',     '复盘报告+邮件纪要合成阅读页'),
    (r'D:\AI research\hkex_di_monitor',    'index.html',     'di.html',      '披露权益监控', '自选股披露权益变动每日提示'),
    (r'D:\AI research\hkex_ann',           'index.html',     'ann.html',     '最新公告',     '自选股披露易最新公告'),
    (r'D:\AI research\southbound_monitor', 'index.html',     'southbound.html','南向资金看板', '17项指标+洋葱策略信号'),
    (r'D:\AI research\hkex_short',         'index.html',     'short.html',   '沽空监控',     '港股自选池每日沽空占比+趋势图'),
]

SITE_NAME = '监控站'


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


TPL = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title><!--TITLE--></title>
<style>
html,body{margin:0;height:100%}
body{background:#0d1117;color:#e6edf3;font-family:system-ui,"Microsoft YaHei",sans-serif}
header{position:fixed;top:0;left:0;right:0;height:52px;background:#0d1117;border-bottom:1px solid #30363d;
display:flex;align-items:stretch;gap:6px;padding:0 12px;overflow-x:auto;z-index:9}
.brand{display:flex;align-items:center;font-weight:600;font-size:15px;margin-right:8px;white-space:nowrap}
.tab{border:none;background:none;color:#8b949e;font-size:14px;font-family:inherit;cursor:pointer;
padding:6px 14px;border-radius:8px;margin:8px 0;display:flex;flex-direction:column;justify-content:center;
line-height:1.35;white-space:nowrap}
.tab:hover{color:#e6edf3;background:#161b22}
.tab.active{color:#e6edf3;background:#161b22}
.tab .ts{font-size:10px;color:#6e7681}
.hint{display:flex;align-items:center;margin-left:auto;font-size:11px;color:#6e7681;white-space:nowrap;padding-right:4px}
.frame{border:none;width:100%;height:calc(100vh - 52px);margin-top:52px;display:none;background:#fff}
.frame.active{display:block}
</style>
</head>
<body>
<header>
<span class="brand">监控站</span>
<!--TABS-->
<span class="hint">每日 09:45 自动更新 · 仅供个人研究</span>
</header>
<main>
<!--FRAMES-->
</main>
<script>
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click', function(){
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
    document.querySelectorAll('.frame').forEach(function(x){x.classList.remove('active')});
    t.classList.add('active');
    var f = document.getElementById('frame-' + t.dataset.f);
    var lazy = f.getAttribute('data-src');
    if (lazy) { f.src = lazy; f.removeAttribute('data-src'); }
    f.classList.add('active');
  });
});
</script>
</body>
</html>'''


def build_index():
    """合并版首页: 顶部 tab + iframe; 第一个 tab 立即加载, 其余首次点击才加载(省流量)"""
    tab_btns = []
    frames = []
    first_done = False
    for src, sname, fname, name, desc in PAGES:
        s = os.path.join(src, sname)
        if not os.path.exists(s):
            print(f'!! 缺 {s}, 该页跳过')
            continue
        ts = datetime.datetime.fromtimestamp(os.path.getmtime(s)).strftime('%m-%d %H:%M')
        if not first_done:
            tab_btns.append(f'<button class="tab active" data-f="{fname}" title="{desc}">'
                            f'{name}<span class="ts">{ts}</span></button>')
            frames.append(f'<iframe id="frame-{fname}" class="frame active" src="{fname}"></iframe>')
            first_done = True
        else:
            tab_btns.append(f'<button class="tab" data-f="{fname}" title="{desc}">'
                            f'{name}<span class="ts">{ts}</span></button>')
            frames.append(f'<iframe id="frame-{fname}" class="frame" data-src="{fname}"></iframe>')
    if not first_done:
        print('!! 一个源页面都没有, 不生成首页')
        return
    html = (TPL.replace('<!--TITLE-->', SITE_NAME)
               .replace('<!--TABS-->', '\n'.join(tab_btns))
               .replace('<!--FRAMES-->', '\n'.join(frames)))
    with open(os.path.join(HERE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html (合并tab版) 生成完毕')


def main():
    check_only = '--check' in sys.argv
    for src, sname, fname, name, desc in PAGES:
        s = os.path.join(src, sname)
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

    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    steps = [
        'git add -A',
        'git diff --cached --quiet && echo NOTHING_TO_COMMIT',
        'git commit -m "auto: update ' + ts + '"',
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
