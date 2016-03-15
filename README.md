# Bus Time Backend

Provides simple Flask-based web server for Bus Time updates backend.

## Local Running

You will need PostgreSQL 9.+, Python 3.3.+ and PIP installed.

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

## Deploying to Heroku

You will need Python 3.+ installed as well as
Heroku account and Heroku Toolbelt set up to work with your account.

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

## Deploying to OpenShift

You will need Python 3.+ installed as well as OpenShift account and
OpenShift Client Tools (RHC) set up to work with your account.

The following steps should be performed from the root directory
of local Bus Time Backend git repository.

1. Create OpenShift domain.

  ```
  $ rhc domain create <domain-name>
  ```

2. Create Python application with PostgreSQL database.

  ```
  $ rhc app create <app-name> python-3.3 postgresql-9.2 --repo . --no-git
  ```

3. Add OpenShift application git repository to local repository remotes.

  ```
  $ git remote add openshift <openshift-git-remote-url>
  ```

4. Push the repository to OpenShift via a convenience script.

  ```
  $ python deploy-openshift.py --force
  ```

  Argument `--force` is required for the first deployment to overwrite
  OpenShift remote repository initial contents.

  By default remote `openshift` is used, but you can specify arbitrary
  remote with `--remote <remote>` argument of the script.
