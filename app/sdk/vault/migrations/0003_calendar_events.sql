-- @fk_off
-- 0003_calendar_events.sql
-- 1) Live calendar store, mirroring the Phase-1 CALENDAR_EVENT overlay
--    payload shape (same pattern as journal_entries / timeline_events).
-- 2) Rebuild timeline_events WITHOUT its two REFERENCES clauses:
--    document_id carries provider storage ids that are never documents
--    rows, and parent_event_id links are app-level (a bounded overlay
--    import can reach a child before its parent). Enforcing either as a
--    hard FK breaks live writes — they are logical references.
-- ISO-8601 datetimes; booleans as INTEGER 0/1.

CREATE TABLE calendar_events (
  id                TEXT PRIMARY KEY,
  title             TEXT NOT NULL,
  description       TEXT,
  start_datetime    TEXT,
  end_datetime      TEXT,
  all_day           INTEGER NOT NULL DEFAULT 0,
  event_type        TEXT NOT NULL DEFAULT 'reminder',
  is_critical       INTEGER NOT NULL DEFAULT 0,
  reminder_days     INTEGER,
  source            TEXT NOT NULL DEFAULT 'manual',
  linked_record_id  TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);

CREATE INDEX idx_calendar_events_start ON calendar_events(start_datetime);
CREATE INDEX idx_calendar_events_source ON calendar_events(source);

CREATE TABLE timeline_events_new (
  id                     TEXT PRIMARY KEY,
  event_type             TEXT NOT NULL,
  title                  TEXT NOT NULL,
  description            TEXT,
  event_date             TEXT,
  event_date_end         TEXT,
  event_status           TEXT,
  parent_event_id        TEXT,
  sequence_number        INTEGER NOT NULL DEFAULT 0,
  source_extraction_id   TEXT,
  footnote_number        INTEGER,
  highlight_color        TEXT,
  urgency                TEXT NOT NULL DEFAULT 'normal',
  is_deadline            INTEGER NOT NULL DEFAULT 0,
  is_evidence            INTEGER NOT NULL DEFAULT 0,
  document_id            TEXT,
  who_involved           TEXT,
  location               TEXT,
  attached_document_ids  TEXT,     -- JSON array of document ids
  tags                   TEXT,     -- JSON array
  created_at             TEXT NOT NULL,
  updated_at             TEXT NOT NULL
);

INSERT INTO timeline_events_new SELECT * FROM timeline_events;
DROP TABLE timeline_events;
ALTER TABLE timeline_events_new RENAME TO timeline_events;

CREATE INDEX idx_timeline_event_date ON timeline_events(event_date);
CREATE INDEX idx_timeline_document   ON timeline_events(document_id);
CREATE INDEX idx_timeline_parent     ON timeline_events(parent_event_id);
