@echo off
rem Unified monitor push: build site + push merged index.html to Feishu + git publish if remote
rem arg %1 = wave (1 or 2)
cd /d "D:\AI research\monitor_site"
C:\Python314\python.exe -X utf8 push_site.py %1 >> push_site.log 2>&1
