-- Recreates dbo.PainRecords.
-- WARNING: drops the existing table, all of its rows, and any permissions granted on it.
--
-- Run with a login that can create tables in the target database, e.g.:
--   sqlcmd -S PRITI_LAPTOP -U user1 -P <password> -i sql\001_create_pain_records.sql -v DB_NAME=HR_QA_DB

:on error exit

USE [$(DB_NAME)];
GO

DROP TABLE IF EXISTS dbo.PainRecords;
GO

CREATE TABLE dbo.PainRecords (
    id             INT IDENTITY(1, 1) NOT NULL,
    patient_name   NVARCHAR(200)      NOT NULL,
    country        NVARCHAR(100)      NOT NULL,
    pain_level     TINYINT            NOT NULL,
    pain_location  NVARCHAR(200)      NOT NULL,
    occurred_at    DATETIME2(3)       NOT NULL,  -- stored in UTC
    notes          NVARCHAR(2000)     NULL,
    created_at     DATETIME2(3)       NOT NULL CONSTRAINT DF_PainRecords_created_at DEFAULT SYSUTCDATETIME(),
    updated_at     DATETIME2(3)       NULL,
    is_deleted     BIT                NOT NULL CONSTRAINT DF_PainRecords_is_deleted DEFAULT 0,

    CONSTRAINT PK_PainRecords PRIMARY KEY CLUSTERED (id),
    CONSTRAINT CK_PainRecords_pain_level CHECK (pain_level BETWEEN 0 AND 10),
    -- LEN ignores trailing spaces, so whitespace-only values are rejected too.
    CONSTRAINT CK_PainRecords_patient_name CHECK (LEN(patient_name) > 0),
    CONSTRAINT CK_PainRecords_country CHECK (LEN(country) > 0),
    CONSTRAINT CK_PainRecords_pain_location CHECK (LEN(pain_location) > 0)
);
GO

CREATE NONCLUSTERED INDEX IX_PainRecords_country ON dbo.PainRecords (country) INCLUDE (pain_level);
CREATE NONCLUSTERED INDEX IX_PainRecords_occurred_at ON dbo.PainRecords (occurred_at) INCLUDE (pain_level);
GO
