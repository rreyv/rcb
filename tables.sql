CREATE TABLE "created" (
    "PKey" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "match_id" INTEGER NOT NULL,
    "series_id" INTEGER NOT NULL,
    "day" INTEGER NOT NULL,
    "thread_title" TEXT NOT NULL,
    "requestor" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "day_over" INTEGER NOT NULL,
    "created_time" TEXT NOT NULL,
    "sub_id" TEXT NOT NULL
);

CREATE TABLE "match_info" (
    "Pkey" INTEGER PRIMARY KEY AUTOINCREMENT,
    "match_id" INTEGER NOT NULL,
    "series_id" INTEGER NOT NULL,
    "cricinfo_url" TEXT NOT NULL,
    "cricinfo_user" TEXT NOT NULL
);

CREATE TABLE "requested" (
    "Pkey" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "match_id" INTEGER NOT NULL,
    "series_id" INTEGER NOT NULL,
    "day" INTEGER NOT NULL,
    "requestor" TEXT,
    "attempts" INTEGER NOT NULL,
    "thread_name" TEXT NOT NULL,
    "start_date_time" TEXT NOT NULL
);
