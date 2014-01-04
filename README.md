# Bus Time Backend

Provides simple Flask-based web server for Bus Time updates backend.

## Local Running

You will need PostgreSQL 9.+, Python 2.7.+ and PIP installed.

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
  $ pip install --requirement requirements.txt --no-deps
  ```

4. Update database schema.

  ```
  $ alembic -c config/alembic.ini upgrade head
  ```

5. Run server.
  ```
  $ python application.py
  ```

6. Optionally deploy latest Bus Time database. Use [these instructions]
(#deploying-bus-time-database-version), but proceed with local repository,
not remote Heroku one.

## Deploying to Heroku

You will need Heroku account and Heroku Toolbelt set up to work with your account.

1. Create Heroku application.

  ```
  $ heroku apps:create <app-name>
  ```

2. Add PostgreSQL 9.+ addon to the application.

  ```
  $ heroku addons:add heroku-postgresql:dev
    Attached as HEROKU_POSTGRESQL_<COLOR>_URL
    Database has been created and is available
    ...
  ```

3. Promote just created database to be the default one.

  ```
  $ heroku pg:promote HEROKU_POSTGRESQL_<COLOR>_URL
  ```

4. Push the repository to Heroku via a convenience script.

  ```
  $ sh push-to-heroku.sh
  ```

## Deploying Bus Time Database Version

You will need SQLite 3.8.+, SSH, Python 2.7.+ and PIP installed.

1. Generate RSA key pair that will be used for deploy data signing.

  ```
  $ ssh-keygen -t rsa
  ```

  The private key should NOT be protected with passphrase, because as for now PyCrypto does not
  support AES encoding algorithm used by `ssh-keygen` to encrypt private key with passphrase.

2. Push your public key to Heroku.

  ```
  $ cp <public-rsa-key> config
  $ git add .
  $ git commit
  $ sh push-to-heroku.sh
  ```

3. Create configuration file.
  ```
  $ cp config/deploy-bus-time-db.ini.template config/deploy-bus-time-db.ini
  $ vi config/deploy-bus-time-db.ini
  ```

4. Install required Python packages.

  ```
  $ pip install --requirement requirements.txt --no-deps
  ```

5. Deploy latest version available in Bus Time Database repo.

  ```
  $ python deploy-bus-time-db.py
  ```
