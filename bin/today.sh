#!/usr/bin/env bash
# 現在日時を JST で出力する。日付は必ずこれで取得すること。
# 会話の文脈や記憶から日付を推測してはならない。
TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M %a JST'
