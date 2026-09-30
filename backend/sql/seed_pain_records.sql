-- Inserts dummy pain records for testing. Additive: existing rows are not touched.
--   sqlcmd -S PRITI_LAPTOP -U user1 -P <password> -i sql\seed_pain_records.sql -v DB_NAME=HR_QA_DB
--
-- 41 rows: 39 visible through the API and 2 soft-deleted (should never appear).
-- Covers 7 countries, 9 pain locations, every pain level 0-10, April-September 2026,
-- repeat patients, NULL notes, and awkward names (O'Brien, Maria_Lopez, accents).

:on error exit
SET NOCOUNT ON;
SET XACT_ABORT ON;

USE [$(DB_NAME)];
GO

BEGIN TRANSACTION;

INSERT INTO dbo.PainRecords (patient_name, country, pain_level, pain_location, occurred_at, notes)
VALUES
    (N'Asha Patel',       N'India',     7,  N'Lower back', '2026-04-03T09:15:00', N'After lifting boxes at work'),
    (N'Ravi Kumar',       N'India',     3,  N'Knee',       '2026-04-08T18:30:00', NULL),
    (N'Priya Sharma',     N'India',     8,  N'Head',       '2026-04-15T07:05:00', N'Migraine with light sensitivity'),
    (N'Arjun Singh',      N'India',     5,  N'Shoulder',   '2026-04-22T20:45:00', N'Gym injury'),
    (N'Meera Nair',       N'India',     2,  N'Wrist',      '2026-05-02T11:10:00', NULL),
    (N'Vikram Rao',       N'India',     9,  N'Abdomen',    '2026-05-11T03:40:00', N'Went to ER, suspected kidney stone'),
    (N'Kavya Iyer',       N'India',     4,  N'Neck',       '2026-05-19T14:25:00', N'Long hours at desk'),
    (N'Rohan Mehta',      N'India',     6,  N'Lower back', '2026-06-01T08:00:00', NULL),
    (N'John Smith',       N'USA',       9,  N'Head',       '2026-04-05T12:00:00', N'Cluster headache'),
    (N'Emily Johnson',    N'USA',       4,  N'Knee',       '2026-04-19T16:20:00', N'Pain after running'),
    (N'Michael Brown',    N'USA',       6,  N'Lower back', '2026-05-07T10:30:00', NULL),
    (N'Sarah Davis',      N'USA',       2,  N'Ankle',      '2026-05-25T19:00:00', N'Mild sprain, improving'),
    (N'David Wilson',     N'USA',       7,  N'Shoulder',   '2026-06-14T09:45:00', N'Rotator cuff strain'),
    (N'Jessica Miller',   N'USA',       0,  N'Knee',       '2026-07-02T15:00:00', N'Follow-up visit: no pain'),
    (N'Chris Taylor',     N'USA',       10, N'Abdomen',    '2026-07-20T02:15:00', N'Appendicitis, surgery scheduled'),
    (N'Oliver Jones',     N'UK',        5,  N'Neck',       '2026-04-11T13:35:00', NULL),
    (N'Amelia Clarke',    N'UK',        3,  N'Wrist',      '2026-05-14T17:50:00', N'Typing strain'),
    (N'Harry Evans',      N'UK',        8,  N'Lower back', '2026-06-09T06:20:00', N'Cannot bend forward'),
    (N'Sophie Turner',    N'UK',        6,  N'Hip',        '2026-07-08T12:40:00', NULL),
    (N'George Hughes',    N'UK',        1,  N'Head',       '2026-08-03T21:10:00', N'Tension headache, resolved quickly'),
    (N'Liam Tremblay',    N'Canada',    4,  N'Shoulder',   '2026-04-27T10:05:00', NULL),
    (N'Chloe Roy',        N'Canada',    7,  N'Knee',       '2026-06-18T18:15:00', N'Hockey collision'),
    (N'Noah Gagnon',      N'Canada',    5,  N'Lower back', '2026-07-29T09:00:00', N'Worse in cold weather'),
    (N'Emma Martin',      N'Canada',    2,  N'Neck',       '2026-08-21T07:30:00', NULL),
    (N'Jack Wilson',      N'Australia', 6,  N'Ankle',      '2026-05-05T22:00:00', N'Rolled ankle while hiking'),
    (N'Mia Thompson',     N'Australia', 8,  N'Head',       '2026-06-23T11:25:00', N'Migraine'),
    (N'Lucas White',      N'Australia', 3,  N'Hip',        '2026-08-12T16:45:00', NULL),
    (N'Lukas Müller',     N'Germany',   7,  N'Lower back', '2026-05-21T08:50:00', N'Herniated disc suspected'),
    (N'Anna Schmidt',     N'Germany',   4,  N'Wrist',      '2026-07-15T13:00:00', NULL),
    (N'Felix Wagner',     N'Germany',   9,  N'Knee',       '2026-08-27T19:35:00', N'ACL tear'),
    (N'Lucía García',     N'Spain',     5,  N'Neck',       '2026-06-05T10:10:00', N'Whiplash'),
    (N'Pablo Fernández',  N'Spain',     2,  N'Shoulder',   '2026-07-24T15:55:00', NULL),
    (N'Carmen López',     N'Spain',     6,  N'Abdomen',    '2026-09-02T20:20:00', N'Pain after meals'),
    (N'Maria_Lopez',      N'Spain',     3,  N'Knee',       '2026-09-25T10:00:00', N'Underscore in name: search test'),
    (N'Tom O''Brien',     N'UK',        5,  N'Shoulder',   '2026-09-28T17:00:00', NULL),
    -- Repeat patients (follow-up visits)
    (N'Asha Patel',       N'India',     5,  N'Lower back', '2026-09-10T09:00:00', N'Follow-up: better with physiotherapy'),
    (N'John Smith',       N'USA',       7,  N'Head',       '2026-09-14T12:30:00', N'Recurring headache'),
    (N'Priya Sharma',     N'India',     6,  N'Head',       '2026-09-18T07:45:00', NULL),
    (N'Harry Evans',      N'UK',        4,  N'Lower back', '2026-09-22T08:10:00', N'Improving');

-- Soft-deleted rows: the API must never return these or count them in stats.
INSERT INTO dbo.PainRecords (patient_name, country, pain_level, pain_location, occurred_at, notes, is_deleted, updated_at)
VALUES
    (N'Deleted Record One', N'India', 10, N'Head', '2026-09-26T09:00:00', N'Soft-deleted: should not appear in the API', 1, SYSUTCDATETIME()),
    (N'Deleted Record Two', N'USA',   0,  N'Knee', '2026-09-27T09:00:00', N'Soft-deleted: should not appear in the API', 1, SYSUTCDATETIME());

COMMIT TRANSACTION;
GO
