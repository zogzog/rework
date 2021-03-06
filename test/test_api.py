import pytest

from rework.helper import host
from rework import api


def test_task_decorator(cleanup):

    @api.task
    def foo(task):
        pass

    @api.task(domain='babar')
    def bar(task):
        pass


    with pytest.raises(AssertionError) as werr:
        @api.task('nope')
        def nope(task):
            pass

    assert werr.value.args[0] == "Use either @task or @task(domain='domain')"



def reset_ops(engine):
    with engine.begin() as cn:
        cn.execute('delete from rework.operation')
    api.__task_registry__.clear()


def register_tasks():
    @api.task
    def foo(task):
        pass

    @api.task(domain='cheese')
    def cheesy(task):
        pass

    @api.task(domain='ham')
    def hammy(task):
        pass


def test_freeze_ops(engine, cleanup):
    reset_ops(engine)
    register_tasks()
    api.freeze_operations(engine)

    res = engine.execute(
        'select name, domain from rework.operation order by domain, name'
    ).fetchall()
    assert res == [('cheesy', 'cheese'), ('foo', 'default'), ('hammy', 'ham')]

    reset_ops(engine)
    register_tasks()
    api.freeze_operations(engine, domain='default')
    api.freeze_operations(engine, domain='ham')

    res = engine.execute(
        'select name, domain from rework.operation order by domain, name'
    ).fetchall()
    assert res == [('foo', 'default'), ('hammy', 'ham')]


def test_schedule_domain(engine, cleanup):
    reset_ops(engine)
    from . import task_testenv
    from . import task_prodenv

    api.freeze_operations(engine, domain='test')
    api.freeze_operations(engine, domain='production')
    api.freeze_operations(engine, domain='production', hostid='192.168.122.42')

    with pytest.raises(ValueError) as err:
        api.schedule(engine, 'foo')
    assert err.value.args[0] == 'Ambiguous operation selection'


    api.schedule(engine, 'foo', domain='test')
    # there two of them but .schedule will by default pick the one
    # matching the *current* host
    api.schedule(engine, 'foo', domain='production')
    api.schedule(engine, 'foo', domain='production', hostid='192.168.122.42')
    api.schedule(engine, 'foo', domain='production', hostid=host())

    hosts = [
        host for host, in engine.execute(
            'select host from rework.task as t, rework.operation as op '
            'where t.operation = op.id'
        ).fetchall()
    ]
    assert hosts.count(host()) == 3
    assert hosts.count('192.168.122.42') == 1

    with pytest.raises(Exception):
        api.schedule(engine, 'foo', domain='production', hostid='172.16.0.1')

    with pytest.raises(Exception):
        api.schedule(engine, 'foo', domain='bogusdomain')
