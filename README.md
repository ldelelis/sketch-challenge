# Sketch Challenge - Lucio Delelis
---

- [Getting started](#getting-started)
  - [Setup](#setup)
  - [Operations](#operations)
- [External services](#external-services)

# Getting started
## Setup

Dependencies for the project can be installed with `pip install -r requirements.txt`. Using a virtualenv is suggested:
`python3 -m venv env` will create a virtual environment with your current python version under an `env/` directory.

Some environment variables are required to start using the project. [direnv](https://direnv.net/) is suggested (but not required) for this:

* DB_CONN_STRING: a connection string used for database access. Required by the seeding script and the project
* DB_USER: Default username for database bootstrap
* DB_PASS: Default admin password for database bootstrap
* DB_NAME: Initial database name for database bootstrap
* AWS_ACCESS_KEY_ID: Access key for S3. It's used by MinIO, and thus it doesn't required a valid AWS format
* AWS_SECRET_ACCESS_KEY: Secret access key for S3. Same as above regarding format
* S3_ENDPOINT_URL: Connection URL for S3. It's required due to MinIO. If using S3 on AWS it's not needed

## Operations

Common project operations are declared on `tasks.py`, using the [Invoke](https://www.pyinvoke.org/) library.

* `inv bootstrap`: starts the project environment (MinIO for S3, and PostgreSQL for database) in the background, and prepares its initial resources for usage
* `inv seed <number>`: Seeds the database and object storage with <number> objects, to test locally
* `inv bench <name>`: Runs a cProfile benchmark with debug mode enabled, saves its result under `profiles/<name>.prof`, and open its visualization in a browser using `snakeviz`
* `inv run`: Runs the script
* `inv teardown`: Destroys the project environment, stopping services and deleting their volumes

# External services

The assignment required any S3-compatible object storage, and a RDBMS (postgreSQL being suggested).

I went with MinIO for object storage, since it provides an S3-compatible API for local storage, and it lessens the
burden of setup and permission management. If a cloud bucket were to be used, some extra scripting would be necessary
to automate permissions. This could be done with Terraform and any helper scripts deemed fit.
