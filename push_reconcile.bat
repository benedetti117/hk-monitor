@echo off
rem Push reconcile loop body (runs every 10min via Task Scheduler)
cd /d "D:\AI research\monitor_site"
C:\Python314\python.exe -X utf8 push_reconcile.py
