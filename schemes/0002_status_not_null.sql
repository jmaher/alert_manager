USE alerts;
UPDATE alerts SET status='NEW' WHERE status='' or status IS NULL;
ALTER TABLE alerts MODIFY status VARCHAR(64) NOT NULL DEFAULT 'NEW';
COMMIT;
