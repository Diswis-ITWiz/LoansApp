# DSWS Loans Application

The Loans App is designed to be an internal web application facilitate, track, and oversee loans transactions for the DSWS loans committee.

## Prerequisites

- Python 3.10-3.12. The pinned dependency set is not intended for Python 3.13+ without package upgrades.
- XAMPP or another local MySQL server
- MySQL client build prerequisites required by `mysqlclient`

## Setup

From this project directory, create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\activate
```

Install the pinned Python dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a MySQL database for the application, then copy the environment template:

```powershell
copy .env.example .env
```

Edit `.env` with the real database credentials, Django secret key, and Gmail app password.

Apply migrations and create an admin user:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

## Run The Application

Start the development server from the project directory:

```powershell
python manage.py runserver
```

On Windows, `startup.bat` performs the same project-local startup after `.venv` has been created and dependencies have been installed:

```powershell
.\startup.bat
```

You can pass normal Django `runserver` arguments through the script:

```powershell
.\startup.bat 127.0.0.1:8001
```

## Run Tests

The test settings use SQLite and dummy email settings so tests can run without a local `.env` or MySQL database:

```powershell
python manage.py test --settings=loans.test_settings
```

## Email Reminder Commands

These management commands can be run manually or scheduled with Windows Task Scheduler:

```powershell
python manage.py senddeadlineemails
python manage.py sendoverdueitemaemails
python manage.py sendoverdueitembemails
```
