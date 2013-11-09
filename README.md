# Bus Time Backend

Provides simple Flask-based web server for Bus Time updates backend.


## Running

You will need PostgreSQL 9.x, Sqlite 3.8.x, Python 2.7 and PIP installed.

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

You will need Heroku account with and Heroku Toolbelt set up to work with your account. The following should be done from repository root directory.

1. Create Heroku application:

        $ heroku apps:create <app-name>
This will create a Heroku application and add a `heroku` remote to the repository.

2. Add PostgreSQL 9.x (seems to be 9.3 now) addon to the application:

        $ heroku addons:add heroku-postgresql:dev
          Attached as HEROKU_POSTGRESQL_<COLOR>_URL
          Database has been created and is available
          ...

3. Promote just created database to be a default one so that its URL will be accessible via `DATABASE_URL` evironment variable:

        $ heroku pg:promote HEROKU_POSTGRESQL_<COLOR>_URL
Note: use appropriate color name instead of `<COLOR>` part.

5. Push the repository to Heroku via a convenience script:

        $ ./push-to-heroku
The repository will be pushed and a web server will start.


### Notes

Script `push-to-heroku` currently pushes from `heroku-support` local branch to Heroku `master` branch. This should be changed when `heroku-support` moves to `master`.
