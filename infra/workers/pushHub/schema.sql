CREATE TABLE IF NOT EXISTS subscriptions (
  endpoint TEXT PRIMARY KEY,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  uaClass TEXT NOT NULL DEFAULT 'other',
  createdAt TEXT NOT NULL,
  lastSeenAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS topicSubs (
  endpoint TEXT NOT NULL,
  topic TEXT NOT NULL,
  subscribedAt TEXT NOT NULL,
  PRIMARY KEY (endpoint, topic),
  FOREIGN KEY (endpoint) REFERENCES subscriptions(endpoint) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS topicSubsTopicIdx ON topicSubs (topic);

CREATE TABLE IF NOT EXISTS sentNonce (
  nonce TEXT PRIMARY KEY,
  ts INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS sentNonceTsIdx ON sentNonce (ts);
