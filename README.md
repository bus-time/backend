# Bus Time Backend

Provides simple Flask-based web server for Bus Time updates backend.


## Running

You will need PostgreSQL 9.x, Python 2.7 and PIP installed.

1. Create empty PostgreSQL database for the Backend.

2. Create Backend configuration file based on `backend.ini.template`.

3. Install required Python packages:

        $ pip install -r requirements.txt

4. Update database scheme:

        $ alembic upgrade head

5. Optionally deploy latest Bus Time database:

        $ python application --deploy-version

6. Run web server:

        $ python application --run-server


## Deploying to Heroku

You will need Heroku account with and Heroku Toolbelt set up to work with your account. The
following should be done from repository root directory.

1. Create Heroku application:

        $ heroku apps:create <app-name>
This will create a Heroku application and add a `heroku` remote to the repository.

2. Add PostgreSQL 9.x (seems to be 9.3 now) addon to the application:

        $ heroku addons:add heroku-postgresql:dev
          Attached as HEROKU_POSTGRESQL_<COLOR>_URL
          Database has been created and is available
          ...

3. Promote just created database to be a default one so that its URL will be accessible via
`DATABASE_URL` evironment variable:

        $ heroku pg:promote HEROKU_POSTGRESQL_<COLOR>_URL
Note: use appropriate color name instead of `<COLOR>` part.

5. Push the repository to Heroku via a convenience script:

        $ ./push-to-heroku
The repository will be pushed and a web server will start.


## Deploying Bus Time Database Version

You will need SQLite 3.8.x, SSH keygen tool, Python 2.7 and PIP installed.

1. Generate RSA key pair that will be used for deploy data signing:

        $ ssh-keygen -t rsa
The private key should NOT be protected with passphrase, because as for now PyCrypto does not
support AES encoding algorithm used by `ssh-keygen` to encrypt private key with passphrase.

2. Make sure that your public key has `.pub` suffix and is commited into
`<REPO>/backend/deployment-keys/` directory and pushed to Heroku.

3. Install required Python packages from `requirements.txt` just like in the section *Running*
if you haven’t done it yet.

3. Deploy latest version available in Bus Time Database repo:

        $ python deploy-bus-time-db.py -f <your-private-rsa-key>
