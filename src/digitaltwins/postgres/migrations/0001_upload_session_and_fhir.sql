-- Unified measurement ingest: upload sessions, FHIR annotation, FHIR status.
-- See docs/decisions/2026-09-28-unified-dataset-ingest-in-digitaltwins-api.md (platform repo).

CREATE TABLE IF NOT EXISTS public.upload_session (
    upload_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    category          varchar(100) NOT NULL,
    name              varchar(255) NOT NULL,
    description       text,
    source_kind       varchar(20)  NOT NULL CHECK (source_kind IN ('folder', 'zip')),
    commit_mode       varchar(20)  NOT NULL DEFAULT 'on_finalize'
                      CHECK (commit_mode IN ('on_finalize', 'on_approve')),
    status            varchar(20)  NOT NULL DEFAULT 'receiving'
                      CHECK (status IN ('receiving', 'staged', 'processing', 'completed', 'failed')),
    failure_stage     varchar(50),
    failure_message   text,
    fhir_mode         varchar(20)  NOT NULL DEFAULT 'none'
                      CHECK (fhir_mode IN ('none', 'auto', 'descriptions')),
    fhir_descriptions jsonb,
    dataset_uuid      uuid REFERENCES public.dataset (dataset_uuid) ON DELETE SET NULL,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS upload_session_status_idx ON public.upload_session (status);

CREATE TABLE IF NOT EXISTS public.dataset_fhir_annotation (
    dataset_uuid uuid PRIMARY KEY REFERENCES public.dataset (dataset_uuid) ON DELETE CASCADE,
    descriptions jsonb       NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.dataset
    ADD COLUMN IF NOT EXISTS fhir_status varchar(20) NOT NULL DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS fhir_failure_message text,
    -- Existing rows get the migration time; new rows their registration time.
    ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE public.dataset
    ADD CONSTRAINT dataset_fhir_status_check
    CHECK (fhir_status IN ('none', 'pending', 'pushing', 'completed', 'failed'));
