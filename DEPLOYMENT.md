# Deployment Guide for SecureBank

## The Problem
Vercel's serverless environment doesn't allow writing to the filesystem, so SQLite databases don't work in production. You need to use PostgreSQL.

## Solution: Set Up PostgreSQL Database

### Option 1: Vercel Postgres (Recommended)

1. **Go to your Vercel Dashboard**
2. **Navigate to your project**
3. **Go to Storage tab**
4. **Click "Create Database"**
5. **Select "Postgres"**
6. **Choose a plan** (Hobby plan is free)
7. **Select a region** (choose closest to your users)
8. **Click "Create"**

### Option 2: Supabase (Free Alternative)

1. **Go to [supabase.com](https://supabase.com)**
2. **Sign up for free account**
3. **Create a new project**
4. **Go to Settings > Database**
5. **Copy the connection string**

### Option 3: Railway (Another Free Option)

1. **Go to [railway.app](https://railway.app)**
2. **Sign up with GitHub**
3. **Create a new project**
4. **Add PostgreSQL service**
5. **Copy the connection string**

## Configure Environment Variables

In your Vercel project settings, add these environment variables:

```
SECRET_KEY=your-secure-secret-key-here
DEBUG=False
DATABASE_URL=your-postgresql-connection-string
```

### Generate a Secure Secret Key

Run this command to generate a secure secret key:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Database Connection String Format

Your DATABASE_URL should look like this:
```
postgresql://username:password@host:port/database_name
```

## Deploy to Vercel

1. **Push your code to GitHub** (already done)
2. **Connect your repository to Vercel**
3. **Set environment variables**
4. **Deploy**

## Post-Deployment Setup

After deployment, you need to run migrations:

### Method 1: Vercel Functions (Recommended)

Create a new file `api/migrate.py`:

```python
from django.core.management import execute_from_command_line
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bankproject.settings')
django.setup()

def handler(request):
    execute_from_command_line(['manage.py', 'migrate'])
    return {'status': 'Migrations completed'}
```

### Method 2: Local Migration

1. **Set your local environment variables**:
```bash
export DATABASE_URL=your-production-database-url
export SECRET_KEY=your-production-secret-key
export DEBUG=False
```

2. **Run migrations locally**:
```bash
python3 manage.py migrate
```

3. **Create superuser**:
```bash
python3 manage.py createsuperuser
```

## Test Your Deployment

1. **Visit your Vercel URL**
2. **Try to login**
3. **Test all features**
4. **Check admin panel**

## Troubleshooting

### Common Issues:

1. **"Database connection failed"**
   - Check your DATABASE_URL format
   - Ensure database is accessible from Vercel

2. **"No module named 'psycopg2'"**
   - Make sure `psycopg2-binary` is in requirements.txt

3. **"Permission denied"**
   - Check database user permissions
   - Ensure database allows external connections

4. **"Table doesn't exist"**
   - Run migrations: `python3 manage.py migrate`

## Security Notes

- Never commit your SECRET_KEY or DATABASE_URL to Git
- Use environment variables for all sensitive data
- Enable SSL for database connections
- Use strong passwords for database users

## Support

If you encounter issues:
1. Check Vercel deployment logs
2. Verify environment variables
3. Test database connection locally
4. Check Django error logs 