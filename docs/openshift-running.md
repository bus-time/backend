# Deploying to OpenShift

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
  $ python deploy/openshift.py --force
  ```

  Argument `--force` is required for the first deployment to overwrite
  OpenShift remote repository initial contents.

  By default remote `openshift` is used, but you can specify arbitrary
  remote with `--remote <remote>` argument of the script.
