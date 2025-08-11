@echo off
REM 本番環境設定スクリプト
echo 本番環境モードに設定します...
set APP_ENV=production
set PYTHONIOENCODING=utf-8
echo APP_ENV=%APP_ENV%
echo 本番環境設定完了
echo 警告: 本番データを使用します！