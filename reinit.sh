cp samples.db samples.db.backup.$(date +%Y%m%d_%H%M%S)
rm -f samples.db
sqlite3 samples.db < "SQL queries.txt"
sqlite3 samples.db ".tables"
sqlite3 samples.db "SELECT COUNT() AS test_runs FROM TestRun;"
sqlite3 samples.db "SELECT COUNT() AS measurements FROM TestMeasurement;"
python flaskMain.py