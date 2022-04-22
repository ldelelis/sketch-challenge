5,000 images were generated using the seeding script as a way to benchmark script execution
DB Record updates were also disabled via the use of a `DEBUG` flag, in order to rerun benchmarks
without the need to re-seed the environment

# 1st iteration

Duration with s3 resources: 280s
Duration with s3 client: 181s

* No observable memory leaks, thanks to [memray](https://github.com/bloomberg/memray)
* Observing a cProfile generation with [snakeviz](https://jiffyclub.github.io/snakeviz/) displayed a lot of overhead from boto3 resources (see `profiles/1st_resources.prof`)
    * After changing usage to boto's low level client, execution time almost halved.
    * Instantiation of boto's `Bucket` and `Object` seems to scale poorly on iterations

# 2nd iteration

Duration with bulk update: 175s

Memory footprint changes were negligible by duplicating the allocation space of the list of ids.
Computation benefits weren't satisfactory, as only about 6 seconds were shaved off of execution time

According to the resulting profile, the vast majority of execution time is spent on API calls to s3.
