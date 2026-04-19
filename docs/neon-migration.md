# Neon Migration Guide

This project can use either:

- local SQLite for quick development
- Neon Postgres through `DATABASE_URL`

The app now follows this rule:

- if `DATABASE_URL` is set, Django uses that database
- if `DATABASE_URL` is not set and `DEBUG=True`, Django uses `db.sqlite3`
- if `DATABASE_URL` is not set and `DEBUG=False`, Django fails fast

## Goal

Move existing data from local SQLite into Neon, then point Railway at Neon so deploys stop wiping the database.

## 1. Back up local SQLite

Run this from `backend/`:

```powershell
Copy-Item db.sqlite3 db.backup-2026-04-11.sqlite3
```

## 2. Export data from local SQLite

Open a fresh terminal and run from `backend/`:

```powershell
$env:DEBUG="True"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
..\.venv\Scripts\python.exe manage.py dumpdata --exclude auth.permission --exclude contenttypes > data.json
```

## 3. Create a Neon database target

In Neon:

1. Open the project.
2. Use the `production` branch for Railway.
3. Create a second branch like `local-dev` for your laptop.
4. Copy each branch connection string from the `Connect` button.

Neon branches are isolated copy-on-write clones, so using a separate local branch is safe.

## 4. Prepare Neon schema

Point your terminal at the Neon `production` branch first:

```powershell
$env:DEBUG="False"
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST/DB?sslmode=require"
..\.venv\Scripts\python.exe manage.py migrate
```

This creates tables in Neon before loading data.

## 5. Import data into Neon

Still using the Neon `production` branch connection string:

```powershell
..\.venv\Scripts\python.exe manage.py loaddata data.json
```

## 6. Verify row counts in Neon

In the Neon SQL editor, run:

```sql
select count(*) as stock_count from api_stock;
select count(*) as stockdata_count from api_stockdata;
select count(*) as wishlist_count from api_wishlist;
select count(*) as user_count from auth_user;
```

These counts should match the data you exported from local SQLite.

## 7. Point Railway at Neon

In Railway Variables:

1. Set `DATABASE_URL` to the Neon `production` branch connection string.
2. Click `Add` or otherwise save the variable so it is actually applied.
3. Redeploy the service.

After this, Railway should stop storing data inside the app container.

## 8. Point local development at Neon

For local development, use your Neon `local-dev` branch connection string in `.env`:

```env
DEBUG=True
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require
```

Because `DATABASE_URL` takes priority, local Django will read from Neon even with `DEBUG=True`.

## 9. Keep a rollback path

Do not delete these right away:

- `db.sqlite3`
- `db.backup-2026-04-11.sqlite3`
- `data.json`

Keep them until Railway has deployed successfully and your app data survives at least one more deployment.
