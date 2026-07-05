create table if not exists thumb_files (
  id bigserial primary key,
  chat_id bigint not null,
  kind text not null,
  file_id text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_thumb_files_chat_kind on thumb_files (chat_id, kind);
