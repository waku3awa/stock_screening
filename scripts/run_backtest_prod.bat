@echo off
REM 本番環境でバックテスト実行
echo 本番環境でバックテストを実行します...
echo 警告: 本番データを使用します！
echo APP_ENV=production> .env.current
set PYTHONIOENCODING=utf-8
uv run python src/backtest.py
echo 本番環境バックテスト完了