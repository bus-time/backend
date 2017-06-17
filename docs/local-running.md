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
  
5. Generate RSA key pair to use for database deployment signing.
  ```
  $ ssh-keygen -t rsa -b 4096 -C "your-email@example.com" -N "" -f /key/pair/path/bustime
  ```
  
6. Move public key `/key/pair/path/bustime.pub` to `~/.ssh/` directory so that
  the backend can find it when verifying a signature.
  
7. Move private key `/key/pair/path/bustime` somewhere safe and use it when
  deploying new database version.

8. Run the server.

  ```
  $ python application.py
  ```

9. Optionally deploy the latest Bus Time database.
