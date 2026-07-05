create table if not exists thumb_files (
  id bigserial primary key,
  chat_id bigint not null,
  kind text not null,
  file_id text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_thumb_files_chat_kind on thumb_files (chat_id, kind);

create table if not exists yt_video_map (
  chat_id bigint not null,
  link_msg_id bigint not null,
  video_msg_id bigint not null,
  created_at timestamptz not null default now(),
  primary key (chat_id, link_msg_id)
);
