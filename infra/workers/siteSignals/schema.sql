CREATE TABLE IF NOT EXISTS dailySignals (
  signalDate TEXT NOT NULL,
  path TEXT NOT NULL,
  eventName TEXT NOT NULL,
  bucket TEXT NOT NULL DEFAULT '',
  target TEXT NOT NULL DEFAULT '',
  count INTEGER NOT NULL DEFAULT 0,
  updatedAt TEXT NOT NULL,
  PRIMARY KEY (signalDate, path, eventName, bucket, target)
);

CREATE INDEX IF NOT EXISTS dailySignalsDateEventIdx
  ON dailySignals (signalDate, eventName);

CREATE INDEX IF NOT EXISTS dailySignalsPathIdx
  ON dailySignals (path);
