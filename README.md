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
  $ mv backend.ini.template backend.ini
  $ vi backend.ini
  ```

3. Install required Python packages.

  ```
  $ pip install --requirement requirements.txt
  ```

4. Update database schema.

  ```
  $ alembic upgrade head
  ```

5. Deploy latest Bus Time database.

  ```
  $ python application --deploy-version
  ```

6. Run server.

  ```
  $ python application --run-server
  ```

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

3. Promote just created database to be a default one so that its URL will be accessible via
`DATABASE_URL` evironment variable.

  ```
  $ heroku pg:promote HEROKU_POSTGRESQL_<COLOR>_URL
  ```

5. Push the repository to Heroku via a convenience script.

  ```
  $ ./push-to-heroku
  ```

## Deploying Bus Time Database Version

You will need SQLite 3.8.+, SSH keygen tool, Python 2.7.+ and PIP installed.

1. Generate RSA key pair that will be used for deploy data signing.

  ```
  $ ssh-keygen -t rsa
  ```

  The private key should NOT be protected with passphrase, because as for now PyCrypto does not
  support AES encoding algorithm used by `ssh-keygen` to encrypt private key with passphrase.

2. Push your public key to Heroku.

  ```
  $ cp <public-rsa-key> backend/deployment-keys
  $ git push heroku master
  ```

3. Install required Python packages.

  ```
  $ pip install --requirement requirements.txt
  ```

4. Deploy latest version available in Bus Time Database repo.

  ```
  $ python deploy-bus-time-db.py -f <private-rsa-key>
  ```
