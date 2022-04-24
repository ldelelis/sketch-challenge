from invoke import task


@task
def bootstrap(c):
    c.run('docker-compose up -d')
    c.run('docker-compose exec buckets mkdir /data/legacy-s3 /data/production-s3')


@task
def teardown(c):
    c.run('docker-compose down -v')


@task
def seed(c, count):
    c.run(f"python bin/sre-challenge-addon1.py {count}")


@task
def bench(c, bench_name):
    filename = f"profiles/{bench_name}.prof"
    c.run(f"DEBUG=true python -m cProfile -o {filename} challenge/main.py")
    c.run(f"snakeviz {filename}")


@task
def run(c):
    c.run("python challenge/main.py")
