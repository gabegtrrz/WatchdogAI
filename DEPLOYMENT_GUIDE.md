# WatchdogAI Railway Deployment Guide

This guide will help you deploy your Django application to Railway quickly and efficiently.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Git Repository**: Your code should be in a Git repository (GitHub, GitLab, etc.)
3. **Environment Variables**: Prepare your environment variables

## Step 1: Prepare Your Repository

### 1.1 Environment Variables

Create a `.env` file locally with your production environment variables:

```bash
# Django Settings
SECRET_KEY=your-super-secret-key-here
DEBUG=False

# Database (Railway will provide these)
PGDATABASE=your-database-name
PGUSER=your-database-user
PGPASSWORD=your-database-password
PGHOST=your-database-host
PGPORT=5432

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Frontend URL (if applicable)
FRONTEND_URL=https://your-frontend-domain.com
```

### 1.2 Generate Django Secret Key

Generate a new secret key for production:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Step 2: Deploy to Railway

### 2.1 Connect Your Repository

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect it's a Python project

### 2.2 Configure Environment Variables

1. In your Railway project dashboard, go to "Variables"
2. Add all the environment variables from your `.env` file
3. **Important**: Set `DEBUG=False` for production

### 2.3 Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically provide the database connection variables

### 2.4 Add Redis (Optional - for Celery)

1. In your Railway project, click "New"
2. Select "Database" → "Redis"
3. Railway will provide the `REDIS_URL` variable

## Step 3: Deploy

### 3.1 Automatic Deployment

Railway will automatically:

- Install dependencies from `requirements.txt`
- Run migrations
- Collect static files
- Start the application with Gunicorn

### 3.2 Manual Commands (if needed)

If you need to run commands manually:

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser (optional)
python manage.py createsuperuser

# Start the application
gunicorn watchdog_ai.wsgi:application --bind 0.0.0.0:$PORT
```

## Step 4: Verify Deployment

### 4.1 Check Application Status

1. Go to your Railway project dashboard
2. Check the "Deployments" tab for deployment status
3. Verify the application is running

### 4.2 Test Your Application

1. Click on your application URL in Railway
2. Test the main functionality
3. Check Django admin at `/admin/`

### 4.3 Monitor Logs

1. In Railway dashboard, go to "Deployments"
2. Click on your deployment
3. Check logs for any errors

## Step 5: Post-Deployment Setup

### 5.1 Create Superuser

```bash
# Connect to your Railway app via CLI
railway login
railway link
railway run python manage.py createsuperuser
```

### 5.2 Load Initial Data (if needed)

```bash
railway run python manage.py loaddata your_fixture.json
```

### 5.3 Set up Custom Domain (Optional)

1. In Railway dashboard, go to "Settings"
2. Add your custom domain
3. Configure DNS settings

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

- Verify all PostgreSQL environment variables are set
- Check that the database service is running
- Ensure `psycopg2-binary` is in requirements.txt

#### 2. Static Files Not Loading

- Verify `whitenoise` is in requirements.txt
- Check that `collectstatic` command ran successfully
- Ensure `STATIC_ROOT` is properly configured

#### 3. Application Won't Start

- Check logs in Railway dashboard
- Verify `gunicorn` is in requirements.txt
- Ensure `Procfile` is in the root directory

#### 4. Environment Variables Not Loading

- Verify all variables are set in Railway dashboard
- Check variable names match your settings
- Restart deployment after adding variables

### Debug Mode

For debugging, temporarily set `DEBUG=True` in Railway variables, but remember to set it back to `False` for production.

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] `SECRET_KEY` is set and secure
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] Database credentials are secure
- [ ] Email credentials are secure
- [ ] HTTPS is enabled (Railway provides this automatically)

## Performance Optimization

1. **Database**: Railway PostgreSQL is optimized for production
2. **Static Files**: Whitenoise serves static files efficiently
3. **Caching**: Consider adding Redis for caching
4. **Monitoring**: Use Railway's built-in monitoring

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Django Deployment: [docs.djangoproject.com](https://docs.djangoproject.com/en/stable/howto/deployment/)
- Project Issues: Check your project's issue tracker

## Quick Commands Reference

```bash
# Deploy to Railway
git push origin main

# Check deployment status
railway status

# View logs
railway logs

# Run Django commands
railway run python manage.py [command]

# Connect to database
railway run psql $DATABASE_URL
```

Your application should now be live on Railway! 🚀
