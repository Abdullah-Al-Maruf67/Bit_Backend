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

5. Create a superuser (optional):
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
├── data/               # Main app
│   ├── models.py       # Database models
│   └── views.py        # View functions
├── accounts/           # User authentication app
├── requirements.txt    # Project dependencies
└── manage.py           # Django management script
```

## API Documentation

[Add API documentation here or link to your API docs]

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
