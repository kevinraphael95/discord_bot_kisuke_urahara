# 🗄️ SQL — Création des tables pour le bot

Copier-coller le code ci-dessous dans SQL Editor pour créer toutes les tables nécessaires.

# 1️⃣ Table `bot_lock`

```sql
CREATE TABLE public.bot_lock (
    id TEXT NOT NULL,
    instance_id TEXT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT now(),
    CONSTRAINT bot_lock_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;
```

# 2️⃣ Table `bot_settings`

```sql
CREATE TABLE public.bot_settings (
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    CONSTRAINT bot_settings_pkey PRIMARY KEY (key)
) TABLESPACE pg_default;
```

# 3️⃣ Table `reiatsu`

```sql
CREATE TABLE public.reiatsu (
    user_id BIGINT PRIMARY KEY,                    -- ID Discord de l'utilisateur
    username TEXT NOT NULL,                        -- Nom de l'utilisateur
    points BIGINT DEFAULT 0,                       -- Reiatsu actuel
    bonus5 INT DEFAULT 0,                          -- Bonus éventuel
    last_steal_attempt TIMESTAMPTZ,               -- Dernière tentative de vol
    steal_cd INT,                                  -- Cooldown vol en heures
    classe TEXT DEFAULT 'Travailleur',            -- Classe de l'utilisateur
    last_skilled_at TIMESTAMPTZ,                  -- Dernière utilisation de skill
    active_skill BOOLEAN DEFAULT FALSE,           -- Si un skill actif est en cours
    fake_spawn_id BIGINT                            -- Pour Illusionniste : ID du faux Reiatsu
) TABLESPACE pg_default;
```

# 4️⃣ Table `reiatsu_config`

```sql
CREATE TABLE public.reiatsu_config (
    guild_id BIGINT PRIMARY KEY,                  -- ID Discord du serveur
    channel_id BIGINT,                             -- ID du salon de spawn
    is_spawn BOOLEAN DEFAULT FALSE,               -- Si un Reiatsu est actuellement apparu
    message_id BIGINT,                             -- ID du message du spawn
    spawn_speed TEXT,                              -- "Ultra_Rapide", "Rapide", "Normal", "Lent"
    last_spawn_at TIMESTAMPTZ,                     -- Timestamp du dernier spawn
    spawn_delay INT                                -- Temps entre deux spawns en secondes
) TABLESPACE pg_default;
```

# 5️⃣ Table `steam_keys`

```sql
CREATE TABLE public.steam_keys (
    id BIGSERIAL NOT NULL,
    game_name TEXT NOT NULL,
    steam_url TEXT NOT NULL,
    steam_key TEXT NOT NULL,
    CONSTRAINT steam_keys_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;
```

# 6️⃣ Table `gardens`

```sql
CREATE TABLE public.gardens (
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    garden_grid JSONB NOT NULL DEFAULT '[
        "🌱🌱🌱🌱🌱🌱🌱🌱",
        "🌱🌱🌱🌱🌱🌱🌱🌱",
        "🌱🌱🌱🌱🌱🌱🌱🌱"
    ]'::jsonb,
    inventory JSONB NOT NULL DEFAULT '{
        "roses": 0,
        "tulipes": 0,
        "hibiscus": 0,
        "jacinthes": 0,
        "tournesols": 0,
        "paquerettes": 0
    }'::jsonb,
    last_fertilize TIMESTAMPTZ NULL,
    potions JSONB NULL,
    armee TEXT NULL,
    argent INTEGER NULL DEFAULT 0,
    CONSTRAINT gardens_pkey PRIMARY KEY (user_id)
) TABLESPACE pg_default;
```

