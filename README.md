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
  $ alembic --config config/alembic.ini upgrade head
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
  $ heroku apps:create --region eu --app <app-name>
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
  $ python deploy-heroku.py
  ```

  By default remote `heroku` is used, but you can specify arbitrary
  remote with `--remote <remote>` argument of the script.

## Deploying Bus Time Database Version

You will need SQLite 3.7.11+, SSH, Python 2.7.+ and PIP installed.

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
  $ python deploy-heroku.py
  ```

3. Create configuration file.
  ```
  $ cp config/deploy-database.ini.template config/deploy-database.ini
  $ vi config/deploy-database.ini
  ```

4. Install required Python packages.

  ```
  $ pip install --requirement requirements.txt --no-deps
  ```

5. Deploy latest version available in Bus Time Database repo.

  ```
  $ python deploy-database.py
  ```

  By default configuration file `config/deploy-database.ini` is used,
  but you can specify arbitrary file with `--config-file <file>` argument
  of the script; `<file>` should reside in `config` directory.

## Usage

### Database Information

#### Request

```
GET /databases/:schema
```

#### Response

```
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 82
```

```json
{
  "schema_version": 2,
  "version": "e6695e5508d5dd7ef6298d57c07c24da7b1a2152"
}
```

### Database Contents

#### Request

```
GET /databases/:schema/contents
```

#### Response

```
HTTP/1.0 200 OK
Content-Type: application/octet-stream
Content-Length: 37412
Content-Disposition: attachment; filename=bus-time.db
Content-Encoding: gzip
X-Content-SHA256: a1e02fa6e5416c12605f923b38d018f725016cd9781951b4deea3301f7ef7eb2
Vary: Accept-Encoding
```
