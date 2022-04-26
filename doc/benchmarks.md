5,000 images were generated using the seeding script as a way to benchmark script execution
DB Record updates were also disabled via the use of a `DEBUG` flag, in order to rerun benchmarks
without the need to re-seed the environment

Tooling used to profile and benchmark was:
* [memray](https://github.com/bloomberg/memray), for memory usage profiling
* The builtin profiles [cProfile](https://docs.python.org/3/library/profile.html#module-cProfile)
* [snakeviz](https://jiffyclub.github.io/snakeviz/) to visualize cProfile's output

# 1st iteration

Duration with s3 resources: 280s
Duration with s3 client: 181s

First naive solution implied instancing two objects on every iteration, as well as saving contents of
the transferred object in memory. By reworking operations into boto3's low level client, runtime was almost
cut in half

# 2nd iteration

Duration with bulk update: 175s

Memory footprint changes were negligible by duplicating the allocation space of the list of ids.
Computation benefits weren't satisfactory, as only about 6 seconds were shaved off of execution time

According to the resulting profile, the vast majority of execution time is spent on API calls to S3.

# 3rd iteration

Duration with direct transfer across buckets: 99s

Reducing the amount of API calls per transfer almost halved execution time once again, as well as
lightening the memory footprint of its execution, by not downloading contents to a bytes buffer between transfers

A furter improvement could be somehow batching these operations together

# 4th iteration

Duration with variable workers: between 10 and 12 seconds

Threading was chosen as means of parallelizing execution, as it performs better with IO-bound tasks.

Using a `ThreadPoolExecutor` allowed the script to parallelize the transfer operations across buckets,
reducing the massive overhead of starting and stopping TCP connections sequentially. This operation is
thread-safe, as Boto3's client is declared thread-safe, unlike Sessions and Resources.

**Caveats**: The tooling doesn't support multithreading the best it can. On one hand, cProfile only reads from
the main thread by default (that is, without manually instrumenting code). On the other hand, the Python
debugger (and by extension, IPDB), behaves oddly when entering multithreaded code. I haven't researched the
alternatives, as the results of my usecases for each were sufficient for this iteration.

Memory footprint increase was also negligible. With a pool of max. 200 workers, an increase of ~20MB heap
size was detected.

# 5th iteration

Duration with reverted bulk update (2nd iteration): ~14s

While working on implementing retry from a partial execution, I noticed a previous optimization didn't allow
for this. However, reverting it also required reimplementing handling of db connections, as this implied running
a db operation on every thread.

For this I used `psycopg2`'s `ThreadedConnectionPool`, which was designed for this use case. Some tweaking was
required around connections, as different combinations of minimum and maximum connections resulted in different
issues. Partly due to postgresql's default `max_connections` value

**NOTE**: this might not be the optimal number of connections. More research and benchmarking is needed
