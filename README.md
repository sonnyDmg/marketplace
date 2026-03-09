# Simple Marketplace Skeleton

This is a minimal Flask marketplace app that works with the same MySQL/phpMyAdmin schema as the larger version.

## Included functionality
- Register
- Log in / log out
- Browse listings
- Filter by category / search by text
- View a single listing
- Create a listing
- View your own listings

## Uses the existing schema
This app is compatible with these tables:
- `users`
- `categories`
- `listings`
- `listing_images` (read-only in this simple version)
- `messages` (not used in this simple version)

## Setup
1. Create/import the database using the previous `schema.sql`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables if needed.

### Example for MAMP on Windows PowerShell
```powershell
$env:DB_HOST="localhost"
$env:DB_USER="root"
$env:DB_PASSWORD="root"
$env:DB_NAME="marketplace_db"
$env:DB_PORT="8889"
python app.py
```

### Example for default MySQL/XAMPP/WAMP
```powershell
$env:DB_HOST="localhost"
$env:DB_USER="root"
$env:DB_PASSWORD=""
$env:DB_NAME="marketplace_db"
$env:DB_PORT="3306"
python app.py
```

Then open:
`http://127.0.0.1:5000`

## Notes
- Keep `app.py` and the `templates/` and `static/` folders together.
- This version intentionally avoids advanced styling and extra features.
- It is meant to be a clean starting point for a class project.
