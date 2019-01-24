#!/bin/sh

LOG_DATE='2019-01-03'

sqlite3 db/logindex.sqlite "delete from logs where source_file='$LOG_DATE'"
curl -d "start=$LOG_DATE" 'http://127.0.0.1:8085/logindex'
