@echo off
REM テスト環境でバックテスト実行
echo テスト環境でバックテストを実行します...
echo APP_ENV=test> .env.current
set PYTHONIOENCODING=utf-8
uv run python src/backtest.py
echo テスト環境バックテスト完了