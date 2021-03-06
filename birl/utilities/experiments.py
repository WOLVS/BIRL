"""
General experiments methods

Copyright (C) 2016-2019 Jiri Borovec <jiri.borovec@fel.cvut.cz>
"""

import os
import sys
import time
import types
import logging
import argparse
import subprocess
# import multiprocessing.pool
import multiprocessing as mproc
from functools import wraps

import tqdm
import numpy as np

from birl.utilities.data_io import create_folder, update_path

#: number of available threads on this computer
NB_THREADS = int(mproc.cpu_count())
#: default date-time format
FORMAT_DATE_TIME = '%Y%m%d-%H%M%S'
#: default logging tile
FILE_LOGS = 'logging.txt'
#: default logging template - log location/source for logging to file
STR_LOG_FORMAT = '%(asctime)s:%(levelname)s@%(filename)s:%(processName)s - %(message)s'
#: default logging template - date-time for logging to file
LOG_FILE_FORMAT = logging.Formatter(STR_LOG_FORMAT, datefmt="%H:%M:%S")


def create_experiment_folder(path_out, dir_name, name='', stamp_unique=True):
    """ create the experiment folder and iterate while there is no available

    :param str path_out: path to the base experiment directory
    :param str name: special experiment name
    :param str dir_name: special folder name
    :param bool stamp_unique: whether add at the end of new folder unique tag

    >>> p_dir = create_experiment_folder('.', 'my_test', stamp_unique=False)
    >>> os.rmdir(p_dir)
    >>> p_dir = create_experiment_folder('.', 'my_test', stamp_unique=True)
    >>> os.rmdir(p_dir)
    """
    assert os.path.exists(path_out), 'missing base folder "%s"' % path_out
    date = time.gmtime()
    if isinstance(name, str) and name:
        dir_name = '{}_{}'.format(dir_name, name)
    path_exp = os.path.join(path_out, dir_name)
    if stamp_unique:
        path_exp += '_' + time.strftime(FORMAT_DATE_TIME, date)
        path_created = None
        while not path_created:
            logging.warning('particular out folder already exists')
            if path_created is not None:
                path_exp += '-' + str(np.random.randint(0, 100))
            path_created = create_folder(path_exp, ok_existing=False)
    else:
        path_created = create_folder(path_exp, ok_existing=False)
    logging.info('created experiment folder "%r"', path_created)
    return path_exp


def release_logger_files():
    """ close all handlers to a file

    >>> release_logger_files()
    >>> len([1 for lh in logging.getLogger().handlers
    ...      if type(lh) is logging.FileHandler])
    0
    """
    for hl in logging.getLogger().handlers:
        if isinstance(hl, logging.FileHandler):
            hl.close()
            logging.getLogger().removeHandler(hl)


def set_experiment_logger(path_out, file_name=FILE_LOGS, reset=True):
    """ set the logger to file

    :param str path_out: path to the output folder
    :param str file_name: log file name
    :param bool reset: reset all previous logging into a file

    >>> set_experiment_logger('.')
    >>> len([1 for lh in logging.getLogger().handlers
    ...      if type(lh) is logging.FileHandler])
    1
    >>> release_logger_files()
    >>> os.remove(FILE_LOGS)
    """
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    if reset:
        release_logger_files()
    path_logger = os.path.join(path_out, file_name)
    fh = logging.FileHandler(path_logger)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(LOG_FILE_FORMAT)
    log.addHandler(fh)


def string_dict(d, headline='DICTIONARY:', offset=25):
    """ format the dictionary into a string

    :param dict d: {str: val} dictionary with parameters
    :param str headline: headline before the printed dictionary
    :param int offset: max size of the string name
    :return str: formatted string

    >>> string_dict({'a': 1, 'b': 2}, 'TEST:', 5)
    'TEST:\\n"a":  1\\n"b":  2'
    """
    template = '{:%is} {}' % offset
    rows = [template.format('"{}":'.format(n), d[n]) for n in sorted(d)]
    s = headline + '\n' + '\n'.join(rows)
    return s


def create_basic_parse():
    """ create the basic arg parses

    :return object:

    >>> parser = create_basic_parse()
    >>> type(parser)
    <class 'argparse.ArgumentParser'>
    >>> parse_arg_params(parser)  # doctest: +SKIP
    """
    # SEE: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--path_cover', type=str, required=True,
                        help='path to the csv cover file')
    parser.add_argument('-d', '--path_dataset', type=str, required=False,
                        help='path to the dataset location, '
                             'if missing in cover', default=None)
    parser.add_argument('-o', '--path_out', type=str, required=True,
                        help='path to the output directory')
    parser.add_argument('--unique', dest='unique', action='store_true',
                        help='whether each experiment have unique time stamp')
    parser.add_argument('--visual', dest='visual', action='store_true',
                        help='whether visualise partial results')
    parser.add_argument('--lock_expt', dest='lock_thread', action='store_true',
                        help='whether lock to run experiment in single thread')
    parser.add_argument('--run_comp_benchmark', action='store_true',
                        help='run computation benchmark on the end')
    parser.add_argument('--nb_workers', type=int, required=False, default=1,
                        help='number of registration running in parallel')
    return parser


def update_paths(args, upper_dirs=None, pattern='path'):
    """ find params with not existing paths

    :param {} args: dictionary with all parameters
    :param [str] upper_dirs: list of keys in parameters
        with item for which only the parent folder must exist
    :param str pattern: patter specifying key with path
    :return [str]: key of missing paths

    >>> update_paths({'sample': 123})[1]
    []
    >>> update_paths({'path_': '.'})[1]
    []
    >>> params = {'path_out': './nothing'}
    >>> update_paths(params)[1]
    ['path_out']
    >>> update_paths(params, upper_dirs=['path_out'])[1]
    []
    """
    if upper_dirs is None:
        upper_dirs = []
    missing = []
    for k in (k for k in args if pattern in k):
        if '*' in os.path.basename(args[k]) or k in upper_dirs:
            p = update_path(os.path.dirname(args[k]))
            args[k] = os.path.join(p, os.path.basename(args[k]))
        else:
            args[k] = update_path(args[k])
            p = args[k]
        if not os.path.exists(p):
            logging.warning('missing "%s": %s', k, p)
            missing.append(k)
    return args, missing


def parse_arg_params(parser, upper_dirs=None):
    """ parse all params

    :param parser: object of parser
    :param [str] upper_dirs: list of keys in parameters
        with item for which only the parent folder must exist
    :return {str: any}:
    """
    # SEE: https://docs.python.org/3/library/argparse.html
    args = vars(parser.parse_args())
    logging.info('ARGUMENTS: \n %r', args)
    # remove all None parameters
    args = {k: args[k] for k in args if args[k] is not None}
    # extend and test all paths in params
    args, missing = update_paths(args, upper_dirs=upper_dirs)
    assert not missing, 'missing paths: %r' % {k: args[k] for k in missing}
    return args


def exec_commands(commands, path_logger=None, timeout=None):
    """ run the given commands in system Command Line

    SEE: https://stackoverflow.com/questions/1996518
    https://www.quora.com/Whats-the-difference-between-os-system-and-subprocess-call-in-Python

    :param [str] commands: commands to be executed
    :param str path_logger: path to the logger
    :param int timeout: timeout for max commands length
    :return bool: whether the commands passed

    >>> exec_commands(('ls', 'ls -l'), path_logger='./sample-output.log')
    True
    >>> exec_commands('mv sample-output.log moved-output.log', timeout=10)
    True
    >>> os.remove('./moved-output.log')
    >>> exec_commands('cp sample-output.log moved-output.log')
    False
    """
    logging.debug('CMD ->> \n%s', commands)
    options = dict(stderr=subprocess.STDOUT)
    # timeout in check_output is not supported by Python 2
    if timeout is not None and timeout > 0 and sys.version_info.major >= 3:
        options['timeout'] = timeout
    if isinstance(commands, str):
        commands = [commands]
    outputs = []
    success = True
    # try to execute all commands in stack
    for cmd in commands:
        outputs += [cmd.encode('utf-8')]
        try:
            outputs += [subprocess.check_output(cmd.split(), **options)]
        except subprocess.CalledProcessError as e:
            logging.exception(commands)
            outputs += [e.output]
            success = False
    # export the output if path exists
    if path_logger is not None and outputs:
        if isinstance(outputs[0], bytes):
            outputs = [out.decode() for out in outputs]
        elif isinstance(outputs[0], str):
            outputs = [out.decode().encode('utf-8') for out in outputs]
        with open(path_logger, 'a') as fp:
            fp.write('\n'.join(outputs))
    return success


# class NonDaemonPool(multiprocessing.pool.Pool):
#     """ We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
#     because the latter is only a wrapper function, not a proper class.
#
#     See: https://github.com/nipy/nipype/pull/2754
#
#     ERROR: fails on Windows
#
#     >>> NonDaemonPool(1)  # doctest: +SKIP
#     """
#     def Process(self, *args, **kwds):
#         proc = super(NonDaemonPool, self).Process(*args, **kwds)
#
#         class NonDaemonProcess(proc.__class__):
#             """Monkey-patch process to ensure it is never daemonized"""
#             @property
#             def daemon(self):
#                 return False
#
#             @daemon.setter
#             def daemon(self, val):
#                 pass
#
#         proc.__class__ = NonDaemonProcess
#         return proc


def wrap_execute_sequence(wrap_func, iterate_vals, nb_workers=NB_THREADS,
                          desc='', ordered=False):
    """ wrapper for execution parallel of single thread as for...

    :param wrap_func: function which will be excited in the iterations
    :param [] iterate_vals: list or iterator which will ide in iterations
    :param int nb_workers: number og jobs running in parallel
    :param str|None desc: description for the bar,
        if it is set None, bar is suppressed
    :param bool ordered: whether enforce ordering in the parallelism

    >>> list(wrap_execute_sequence(np.sqrt, range(5), nb_workers=1, ordered=True))  # doctest: +ELLIPSIS
    [0.0, 1.0, 1.41..., 1.73..., 2.0]
    >>> list(wrap_execute_sequence(sum, [[0, 1]] * 5, nb_workers=2, desc=None))
    [1, 1, 1, 1, 1]
    >>> list(wrap_execute_sequence(max, [[2, 1]] * 5, nb_workers=2, desc=''))
    [2, 2, 2, 2, 2]
    """
    iterate_vals = list(iterate_vals)
    nb_workers = 1 if not nb_workers else int(nb_workers)

    if desc is not None:
        desc = '%r @%i-threads' % (desc, nb_workers)
        tqdm_bar = tqdm.tqdm(total=len(iterate_vals), desc=desc)
    else:
        tqdm_bar = None

    if nb_workers > 1:
        logging.debug('perform parallel in %i threads', nb_workers)
        # Standard mproc.Pool created a demon processes which can be called
        # inside its children, cascade or multiprocessing
        # https://stackoverflow.com/questions/6974695/python-process-pool-non-daemonic
        pool = mproc.Pool(nb_workers)
        pooling = pool.imap if ordered else pool.imap_unordered

        for out in pooling(wrap_func, iterate_vals):
            yield out
            if tqdm_bar is not None:
                tqdm_bar.update()
        pool.close()
        pool.join()
    else:
        logging.debug('perform sequential')
        for out in map(wrap_func, iterate_vals):
            yield out
            if tqdm_bar is not None:
                tqdm_bar.update()


def try_decorator(func):
    """ costume decorator to wrap function in try/except

    :param func:
    :return:
    """
    @wraps(func)
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logging.exception('%r with %r and %r', func.__name__, args, kwargs)
    return wrap


def is_iterable(var):
    """ check if the variable is iterable

    :param var:
    :return bool:

    >>> is_iterable('abc')
    False
    >>> is_iterable([0])
    True
    >>> is_iterable((1, ))
    True
    """
    return any(isinstance(var, cls) for cls in [list, tuple, types.GeneratorType])
