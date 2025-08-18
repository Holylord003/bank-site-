# SecureBank - Django Banking Application

A modern banking application built with Django, featuring user authentication, account management, transactions, and admin features.

## Features

- 🏦 **User Authentication**: Secure login and registration system
- 💳 **Account Management**: Checking and savings accounts
- 💳 **Credit Cards**: Credit card management with payment scheduling
- 💰 **Transactions**: Money transfers, deposits, and transaction history
- 📊 **Admin Dashboard**: Administrative oversight and transaction approval
- 🎨 **Modern UI**: Responsive design with Bootstrap and custom styling
- 🔒 **Security**: CSRF protection, secure forms, and data validation

## Tech Stack

- **Backend**: Django 4.2.7
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: Bootstrap 5, Font Awesome
- **Deployment**: Vercel
- **Static Files**: WhiteNoise

## Local Development

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd bank-page
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create a superuser:
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

6. Visit http://localhost:8000

## Deployment to Vercel

### Prerequisites

- Vercel account
- GitHub repository with your code
- PostgreSQL database (recommended for production)

### Step 1: Prepare Your Repository

Ensure your repository contains all the necessary files:
- `vercel.json`
- `requirements.txt`
- `build_files.sh`
- Updated `settings.py`
- Updated `wsgi.py`

### Step 2: Set Up Database

For production, you'll need a PostgreSQL database. You can use:
- Vercel Postgres
- Supabase
- Railway
- Any other PostgreSQL provider

### Step 3: Deploy to Vercel

1. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Sign in with your GitHub account
   - Click "New Project"
   - Import your GitHub repository

2. **Configure Environment Variables**:
   In your Vercel project settings, add these environment variables:
   ```
   SECRET_KEY=your-secure-secret-key-here
   DEBUG=False
   DATABASE_URL=your-postgresql-connection-string
   ```

3. **Deploy**:
   - Vercel will automatically detect the Django project
   - Click "Deploy"
   - Wait for the build to complete

### Step 4: Post-Deployment Setup

After deployment, you'll need to run migrations:

1. **Access Vercel Functions**:
   - Go to your Vercel dashboard
   - Navigate to Functions
   - Create a new function to run migrations

2. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Create Superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (True/False) | Yes |
| `DATABASE_URL` | Database connection string | Yes (for production) |

## Project Structure

```
bank-page/
├── bankproject/          # Django project settings
├── banking/             # Main banking app
│   ├── models.py        # Database models
│   ├── views.py         # View functions
│   ├── urls.py          # URL patterns
│   └── templates/       # HTML templates
├── static/              # Static files
├── vercel.json          # Vercel configuration
├── requirements.txt     # Python dependencies
├── build_files.sh       # Build script
└── README.md           # This file
```

## Features Overview

### User Features
- **Homepage**: Landing page with services overview
- **Authentication**: Login and registration
- **Dashboard**: Account overview and quick actions
- **Account Management**: View balances and account details
- **Transactions**: Send money, view history
- **Savings**: Open savings account, transfer funds
- **Credit Cards**: Apply for cards, manage payments
- **Scheduled Payments**: Schedule and manage credit card payments

### Admin Features
- **Admin Dashboard**: Overview of system statistics
- **Transaction Approval**: Approve/reject pending transactions
- **User Management**: View and manage user accounts

## Security Features

- CSRF protection on all forms
- Secure password validation
- Session management
- Input validation and sanitization
- SQL injection prevention
- XSS protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, please open an issue in the GitHub repository or contact the development team.
