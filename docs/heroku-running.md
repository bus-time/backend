# Deploying to Heroku

You will need Python 3.4+ installed as well as
Heroku account and Heroku Toolbelt set up to work with your account.

1. Enter the root directory of the backend local git repository copy.
  Create Heroku application. Heroku Toolbelt will add `heroku` remote
  to the repository.

  ```
  $ heroku apps:create --region eu --app <app-name>
  ```

2. Add PostgreSQL 9.+ addon to the application.

  ```
  $ heroku addons:add heroku-postgresql:hobby-dev
    Created postgresql-<code1>-<code2> as DATABASE_URL
    ...
  ```

3. Generate RSA key pair to use for database deployment signing.
  ```
  $ ssh-keygen -t rsa -b 4096 -C "your-email@example.com" -N "" -f /key/pair/path/bustime
  ```

4. Create Heroku config variable with the content of the public key
  `/key/pair/path/bustime.pub` so that the backend can find it when verifying 
  a signature.
  ```
  heroku config:set BUSTIME_PUBLICATION_KEY_<YOUR_NAME>="$(cat /key/pair/path/bustime.pub)"
  ```
  
5. Move private key `/key/pair/path/bustime` somewhere safe and use it when
   deploying a new database version.

6. Push the repository to Heroku via a convenience script.

  ```
  $ python deploy/heroku.py
  ```

  By default remote `heroku` is used, but you can specify arbitrary
  remote with `--remote <remote>` argument of the script.
