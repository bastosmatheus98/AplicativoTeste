# Production Database Seed Guide

## Overview
The database seed is **automatically skipped** in production deployments to ensure fast startup times and avoid initialization timeouts.

## Development vs Production

### Development (auto-seed enabled)
- Seed runs automatically on server start
- Creates Admin user if database is empty
- Username: `Admin`
- Password: `QeBas24`

### Production (auto-seed disabled)
- Seed is **completely skipped** to ensure fast deployment
- Server starts in <5 seconds
- No bcrypt operations during initialization

## Creating Admin User in Production

If you deploy to a fresh database, you have two options:

### Option 1: Run Manual Seed Script
```bash
npm run seed
```

This will:
- Check if users exist
- Create Admin user only if database is empty
- Show credentials in console
- Exit automatically

### Option 2: Create via API/Database

You can create the admin user directly in the database or via SQL:

```sql
INSERT INTO users (name, username, password_hash, role)
VALUES (
  'Queiroz & Bastos Advogados',
  'Admin',
  '$2b$10$YOUR_BCRYPT_HASH_HERE',
  'admin'
);
```

**Note**: Generate bcrypt hash with: `bcrypt.hash("YourPassword", 10)`

## Why Skip Seed in Production?

1. **Fast Deployment**: bcrypt hashing takes 2+ minutes, causing timeout
2. **Reliability**: Database should already be populated in production
3. **Security**: Avoids recreating default credentials on every restart
4. **Flexibility**: Manual seed allows custom admin credentials

## Troubleshooting

### Database has no users after deployment
Run: `npm run seed` after deployment completes

### Need to reset admin password
Update directly in database or use Settings page (requires admin login)

### Deployment still timing out
1. Check DATABASE_URL is configured
2. Verify network connectivity to database
3. Check deployment logs for other errors

## Files Modified
- `server/index-prod.ts`: Removed seed import and call
- `server/seed.ts`: Added production environment check
- `server/seed-prod.ts`: New standalone seed script
