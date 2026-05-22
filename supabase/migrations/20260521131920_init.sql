-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- Backend schema: thesis / chat session tables
-- ============================================================

CREATE TABLE IF NOT EXISTS thesis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query TEXT NOT NULL,
    theme TEXT,
    summary TEXT,
    conviction TEXT CHECK (conviction IN ('High', 'Medium', 'Low')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stock_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thesis_id UUID REFERENCES thesis_sessions(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    name TEXT,
    entry_price NUMERIC(12,2),
    target_price NUMERIC(12,2),
    stop_loss NUMERIC(12,2),
    position_size TEXT,
    fundamentals_score NUMERIC(5,2),
    thematic_fit_score NUMERIC(5,2),
    risk_score NUMERIC(5,2),
    momentum_score NUMERIC(5,2),
    liquidity_score NUMERIC(5,2),
    total_score NUMERIC(5,2),
    rationale TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thesis_id UUID REFERENCES thesis_sessions(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    source TEXT,
    parsed_content TEXT,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES thesis_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for backend tables
CREATE INDEX IF NOT EXISTS idx_sessions_created ON thesis_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stocks_thesis ON stock_recommendations(thesis_id);
CREATE INDEX IF NOT EXISTS idx_docs_thesis ON documents(thesis_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at DESC);

-- ============================================================
-- Frontend schema: chat UI persistence tables (Drizzle ORM)
-- ============================================================

CREATE TABLE IF NOT EXISTS "User" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(64) NOT NULL,
    password VARCHAR(64),
    name TEXT,
    "emailVerified" BOOLEAN NOT NULL DEFAULT false,
    image TEXT,
    "isAnonymous" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "Chat" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "createdAt" TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    "userId" UUID NOT NULL REFERENCES "User"(id),
    visibility VARCHAR NOT NULL DEFAULT 'private' CHECK (visibility IN ('public', 'private'))
);

CREATE TABLE IF NOT EXISTS "Message_v2" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "chatId" UUID NOT NULL REFERENCES "Chat"(id),
    role VARCHAR NOT NULL,
    parts JSONB NOT NULL DEFAULT '[]',
    attachments JSONB NOT NULL DEFAULT '[]',
    "createdAt" TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS "Vote_v2" (
    "chatId" UUID NOT NULL REFERENCES "Chat"(id),
    "messageId" UUID NOT NULL REFERENCES "Message_v2"(id),
    "isUpvoted" BOOLEAN NOT NULL,
    PRIMARY KEY ("chatId", "messageId")
);

CREATE TABLE IF NOT EXISTS "Document" (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    "createdAt" TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    kind VARCHAR NOT NULL DEFAULT 'text' CHECK (kind IN ('text', 'code', 'image', 'sheet')),
    "userId" UUID NOT NULL REFERENCES "User"(id),
    PRIMARY KEY (id, "createdAt")
);

CREATE TABLE IF NOT EXISTS "Suggestion" (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    "documentId" UUID NOT NULL,
    "documentCreatedAt" TIMESTAMPTZ NOT NULL,
    "originalText" TEXT NOT NULL,
    "suggestedText" TEXT NOT NULL,
    description TEXT,
    "isResolved" BOOLEAN NOT NULL DEFAULT false,
    "userId" UUID NOT NULL REFERENCES "User"(id),
    "createdAt" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY ("documentId", "documentCreatedAt") REFERENCES "Document"(id, "createdAt")
);

CREATE TABLE IF NOT EXISTS "Stream" (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    "chatId" UUID NOT NULL REFERENCES "Chat"(id),
    "createdAt" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id)
);

-- ============================================================
-- Row Level Security (RLS) — permissive for demo
-- ============================================================

ALTER TABLE thesis_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all" ON thesis_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON stock_recommendations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON messages FOR ALL USING (true) WITH CHECK (true);
