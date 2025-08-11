@echo off
REM テスト環境設定スクリプト
echo テスト環境モードに設定します...
echo APP_ENV=test> .env.current
set PYTHONIOENCODING=utf-8
echo テスト環境設定完了（.env.testファイルを使用）