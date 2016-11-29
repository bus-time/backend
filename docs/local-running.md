# Local Running

You will need PostgreSQL 9.+, Python 3.4+ and PIP installed.

1. Create empty PostgreSQL database for the Backend.

  ```
  $ createdb <database>
  ```

2. Create configuration file.

  ```
  $ cp config/backend.ini.template config/backend.ini
  $ vi config/backend.ini
  ```

3. Install required Python packages.

  ```
  $ pip install --requirement requirements.txt
  ```

4. Update database schema.

  ```
  $ alembic --config config/alembic.ini upgrade head
  ```

5. Run server.

  ```
  $ python application.py
  ```

6. Optionally deploy latest Bus Time database.
