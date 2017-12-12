import time

from rework import api, monitor
from rework.testutils import scrub, workers


def test_list_operations(engine, cli):
    with workers(engine):
        r = cli('list-operations', engine.url)

        assert """
<X> host(<X>) `<X>.<X>.<X>.<X>` path(print_sleep_and_go_away)
<X> host(<X>) `<X>.<X>.<X>.<X>` path(infinite_loop)
<X> host(<X>) `<X>.<X>.<X>.<X>` path(unstopable_death)
<X> host(<X>) `<X>.<X>.<X>.<X>` path(normal_exception)
<X> host(<X>) `<X>.<X>.<X>.<X>` path(allocate_and_leak_mbytes)
<X> host(<X>) `<X>.<X>.<X>.<X>` path(capture_logs)
<X> host(<X>) `<X>.<X>.<X>.<X>` path(log_swarm)
""".strip() == scrub(r.output).strip()


def test_abort_task(engine, cli):
    url = engine.url
    with workers(engine):
        r = cli('list-workers', url)
        assert '<X> <X>@<X>.<X>.<X>.<X> <X> Mb [running (idle)]' == scrub(r.output)

        t = api.schedule(engine, 'infinite_loop')
        time.sleep(1)  # let the worker pick up the task

        r = cli('list-workers', url)
        assert '<X> <X>@<X>.<X>.<X>.<X> <X> Mb [running #<X>]' == scrub(r.output)

        r = cli('list-tasks', url)
        assert '<X> infinite_loop running [<X>-<X>-<X> <X>:<X>:<X>.<X>+<X>]' == scrub(r.output)

        r = cli('abort-task', url, t.tid)
        t.join()

        r = cli('list-workers', url)
        assert '<X> <X>@<X>.<X>.<X>.<X> <X> Mb [dead] Task <X> aborted' == scrub(r.output)

        r = cli('list-tasks', url)
        assert '<X> infinite_loop aborted [<X>-<X>-<X> <X>:<X>:<X>.<X>+<X>]' == scrub(r.output)


def test_kill_worker(engine, cli):
    url = engine.url
    with engine.connect() as cn:
        cn.execute('delete from rework.worker')

    with workers(engine) as wids:
        api.schedule(engine, 'infinite_loop')
        time.sleep(1)  # let the worker pick up the task

        r = cli('kill-worker', url, wids[0])
        monitor.preemptive_kill(engine)

        r = cli('list-workers', url)
        assert ('<X> <X>@<X>.<X>.<X>.<X> <X> Mb [dead] preemptive kill '
                'at <X>-<X>-<X> <X>:<X>:<X>.<X>'
        ) == scrub(r.output)

        r = cli('list-tasks', url)
        assert '<X> infinite_loop done [<X>-<X>-<X> <X>:<X>:<X>.<X>+<X>]' == scrub(r.output)


def test_shutdown_worker(engine, cli):
    url = engine.url
    with workers(engine) as wids:
        cli('shutdown-worker', url, wids[0])
        time.sleep(1)

        r = cli('list-workers', url)
        assert '<X> <X>@<X>.<X>.<X>.<X> <X> Mb [dead] explicit shutdown' == scrub(r.output)


def test_task_logs(engine, cli):
    with workers(engine):
        t = api.schedule(engine, 'capture_logs')
        time.sleep(1)  # let the worker pick up the task

        r = cli('log-task', engine.url, t.tid)
        assert '\x1b[<X>mmy_app_logger:ERROR: <X>-<X>-<X> <X>:<X>:<X>: will be captured <X>\n\x1b[<X>mstdout:INFO: <X>-<X>-<X> <X>:<X>:<X>: I want to be captured\n\x1b[<X>mmy_app_logger:DEBUG: <X>-<X>-<X> <X>:<X>:<X>: will be captured <X> also' == scrub(r.output)
