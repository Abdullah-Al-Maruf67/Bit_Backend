# Bit Backend

A Django-based backend application for a version control cli tool.

## Prerequisites

- Python 3.8+
- Django 4.0+

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/PROGRAMMING-HEROZSBD/Bit_Backend.git
   cd Bit_Backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Project Structure

```
Bit_Backend/
├── Bit/                 # Main project directory
│   ├── settings.py      # Project settings
│   ├── urls.py         # Main URL configuration
│   └── wsgi.py         # WSGI config
├── data/               # Main app
│   ├── models.py       # Database models
│   └── views.py        # View functions
├── accounts/           # User authentication app
├── requirements.txt    # Project dependencies
└── manage.py           # Django management script
```

## API Documentation

### Authentication

All API endpoints (except registration and login) require authentication using JWT tokens.

#### Register a new user
```http
POST /api/users/register/
Content-Type: application/json

{
    "username": "newuser",
    "email": "user@example.com",
    "password": "securepassword123",
    "password2": "securepassword123"
}
```

#### Login
```http
POST /api/users/login/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

Response includes access and refresh tokens:
```json
{
    "refresh": "your_refresh_token_here",
    "access": "your_access_token_here"
}
```

#### Refresh Token
```http
POST /api/users/token/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token_here"
}
```

#### Logout
```http
POST /api/users/logout/
Authorization: Bearer your_access_token_here
```

### Repositories

#### List all repositories (GET)
```http
GET /api/data/repositories/
Authorization: Bearer your_access_token_here
```

#### Create a new repository (POST)
```http
POST /api/data/repositories/
Authorization: Bearer your_access_token_here
Content-Type: application/json

{
    "name": "My New Repository",
    "description": "A new repository for my project"
}
```

### Commits

#### List all commits for a repository
```http
GET /api/data/commits/?repository=<repository_id>
Authorization: Bearer your_access_token_here
```

#### Create a new commit
```http
POST /api/data/commits/
Authorization: Bearer your_access_token_here
Content-Type: application/json

{
    "repository": 1,
    "message": "Initial commit",
    "files_changed": "main.py, README.md"
}
```

#### Merge a commit
```http
POST /api/data/repositories/<repository_id>/commits/<commit_id>/merge/
Authorization: Bearer your_access_token_here
```

### Share Links

#### Create a shareable link
```http
POST /api/data/share-links/
Authorization: Bearer your_access_token_here
Content-Type: application/json

{
    "repository": 1,
    "expires_at": "2024-12-31T23:59:59Z"
}
```

#### List all share links for a repository
```http
GET /api/data/share-links/?repository=<repository_id>
Authorization: Bearer your_access_token_here
```

## Environment Variables

Create a `.env` file in the root directory and add the following variables:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
```

## Running Tests

```bash
python manage.py test
```

## Contributing

Feel free to submit issues and enhancement requests.
