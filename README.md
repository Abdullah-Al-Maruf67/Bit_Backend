# Bit Backend

A Django-based backend application for a version control system with JWT authentication.

## Prerequisites

- Python 3.8+
- Django 4.0+
- Django REST Framework
- djangorestframework-simplejwt

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Abdullah-Al-Maruf67/Bit_Backend.git
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

5. Create a superuser (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```

6. Run the development server:
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
├── data/               # Main app for repositories and commits
│   ├── models.py       # Database models
│   ├── views.py        # View functions
│   └── urls.py         # API endpoints
├── accounts/           # User authentication app
│   ├── views.py        # Authentication views
│   └── urls.py         # Auth endpoints
├── requirements.txt    # Project dependencies
└── manage.py           # Django management script
```

## API Documentation

### Authentication

#### Register a new user
```http
POST /api/users/register/
Content-Type: application/json

{
    "username": "newuser",
    "password": "securepassword123"
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

#### Verify Token
```http
POST /api/users/verifyaccesstoken/
Content-Type: application/json

{
    "token": "your_access_token_here"
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

#### Get repository details (GET)
```http
GET /api/data/repositories/{id}/
Authorization: Bearer your_access_token_here
```

### Commits

#### List all commits (GET)
```http
GET /api/data/commits/
Authorization: Bearer your_access_token_here
```

#### Create a new commit (POST)
```http
POST /api/data/commits/
Authorization: Bearer your_access_token_here
Content-Type: application/json

{
    "share_token": "your_share_token_here",
    "author": "Author Name",
    "email": "author@example.com",
    "message": "Commit message",
    "parent_hash": "previous_commit_hash",
    "operations": [
        {
            "type": "UPDATE",
            "path": "path/to/file.txt",
            "content": "compressed_file_content"
        },
        {
            "type": "DELETE",
            "path": "path/to/delete.txt"
        }
    ]
}
```

#### Get commit by hash (GET)
```http
GET /api/data/commits/by_hash/?hash={commit_hash}
Authorization: Bearer your_access_token_here
```

#### Merge a commit
```http
POST /api/data/repositories/{repository_id}/commits/{commit_id}/merge/
Authorization: Bearer your_access_token_here
```

### Share Links

#### Create a shareable link (POST)
```http
POST /api/data/share-links/
Authorization: Bearer your_access_token_here
Content-Type: application/json

{
    "repository": 1,
    "expires_at": "2024-12-31T23:59:59Z"
}
```

#### Get repository via share link (GET)
```http
GET /api/data/share-links/{token}/repository/
```

#### Get file via share link (GET)
```http
GET /api/data/share-links/{token}/file/?path=path/to/file.txt
```

## Environment Variables

Create a `.env` file in the root directory and add the following variables:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
```

## Authentication Flow

1. Register a new user at `/api/users/register/`
2. Login at `/api/users/login/` to get access and refresh tokens
3. Include the access token in the `Authorization` header for protected endpoints: `Bearer <access_token>`
4. When the access token expires, use the refresh token at `/api/users/token/refresh/` to get a new access token
5. Use `/api/users/verifyaccesstoken/` to verify if an access token is still valid
6. Logout using `/api/users/logout/` to invalidate the current session

## Contributing

Feel free to submit issues and enhancement requests.
