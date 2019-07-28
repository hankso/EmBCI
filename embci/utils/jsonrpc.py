#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/utils/jsonrpc.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Wed 17 Jul 2019 17:32:41 CST

'''
JSON Remote Procedure Call (JSON-RPC) lightweight and all-in-one-file
implementation, supporting both Python2 & 3.


There are three logical layers of JSON-RPC:

    1 Send/Receive layer :class:JSONRPCServer and :class:JSONRPCClient
        - listen on an address and wait for a JSON-RPC call
        - input response and returned response will be in `bytes`
        - convert between `bytes` and `string` (UTF-8)

    2 Package layer :class:Payload
        - this layer is for RPC 2.0 & 1.0 compatiability
        - package/unpackage objects according to version number

    3 Dispatch layer :class:JSONRPCDispatcher
        - convert between `string` and `object`
        - register functions, handle request and generate response
        - call Payload to check/make the request/response objects


Features
--------
- Positional argument, keyword arugment and both (not define in spec).
- MultiCall, Notifications and mixture of them.
- Mark request as notification at runtime by passing keyword parameters.
- Support both RPC version 1.0 and 2.0


Examples
--------
Server side:
>>> import embci.utils.jsonrpc as jsonrpc
>>> server = jsonrpc.JSONRPCServer(('localhost', 8080))
>>> server.register_introspection_functions()
>>> server.register_function(lambda x, y: x + y, 'add')
>>> server.register_function(lambda *a: sum(a)/len(a), 'average')
>>> server.serve_forever()  # this will block the thread

Client side:
>>> client = jsonrpc.JSONRPCClient('http://localhost:8080')
>>> client.add(10, 12)
22
>>> client.add(10, 12, notify=True)  # server will not response to notification
>>> client._notify.add(10, 12)  # same as above
>>> client.average(10, 12)
11
>>> client.minus(12, 10)
Fault: (-32601, 'Method Not Found - `minus`')

Multiple Call:
>>> multi = MultiCall(client)
>>> multi = client._multicall  # same as above
>>> multi.add(100, 100)
>>> multi.average(range(10))
>>> multi()
<list_iterator at 0x7fa227881d68>
>>> multi(iterator=False)
[200, 4.5]

To use this as a standalone module outside `embci`, check source code and
especially the docstring of `jsonrpc.__external__`.

For debugging:
>>> jsonrpc.debug(True)

Then there will be verbose information like:
JSONRPC --> {"id":"5hq36vw6","jsonrpc":"2.0","method":"system.describe"}
JSONRPC <-- {"id":"5hq36vw6","jsonrpc":"2.0","result":{...}}

Some RPC-relative modules
-------------------------
- jsonrpc2-zeromq-python_: JSON-RPC2.0 over ZeroMQ in Python
- sym-jsonrpc_: A more beautiful symmetric JSON-RPC implementation in python
- Pyro_: PyRO - Python remote objects. It has Pyro4 and Pyro5
- RPyC_: Remote Python Call - A transparent and symmetric RPC Python library


Note on python built-in modules
-------------------------------
XML-RPC is the best choice if you want to implement RPC in Python because
there are built in modules supporting XML-RPC.

+--------------------+---------------+
| Python 2           | Python 3      |
+====================+===============+
| SimpleXMLRPCServer | xmlrpc.server |
| xmlrpclib          | xmlrpc.client |
| xmlrpc.server      | xmlrpc.client |
| xmlrpc.client      | xmlrpc.client |
+--------------------+---------------+

Most of this module is created based on xmlrpc. Some code is modified based
on **jsonrpclib_**.


.. _jsonrpc2-zeromq-python: https://github.com/dwb/jsonrpc2-zeromq-python.git
.. _sym-jsonrpc: https://github.com/niligulmohar/python-symmetric-jsonrpc.git
.. _Pyro: https://github.com/irmen/Pyro5.git
.. _RPyC: https://github.com/tomerfiliba/rpyc.git
.. _jsonrpclib: https://github.com/joshmarshall/jsonrpclib
'''


# =============================================================================
# Modules and Object classes

def __external__():
    '''
    Importing inside this function to avoid the existance of useless module
    names as attributes of this module, resulting in a **clean** namespace.
    '''
    # built-in
    import sys, functools, random, string                          # noqa: E401
    from six import string_types                                   # noqa: W611
    from six.moves import (                                        # noqa: W611
        socketserver, xmlrpc_client, xmlrpc_server, urllib,
        reduce, StringIO
    )

    # filter useless functions
    try:
        del xmlrpc_server.SimpleXMLRPCDispatcher.system_multicall
        del xmlrpc_server.SimpleXMLRPCDispatcher.register_multicall_functions
        del xmlrpc_server.SimpleXMLRPCRequestHandler.is_rpc_path_valid
        del xmlrpc_server.SimpleXMLRPCRequestHandler.accept_encodings
        del xmlrpc_server.SimpleXMLRPCRequestHandler.aepattern
        del xmlrpc_server.SimpleXMLRPCRequestHandler.decode_request_content
    except (AttributeError, NameError):
        pass

    # `embci.utils.jsonrpc` is part of project `EmBCI`, but it also can be
    # used individually like `import jsonrpc`. Functions below are not defined
    # inside this module and need to be imported from other library before
    # using them. To use `jsonrpc` outside `embci` package, just replace few
    # lines below with proper importing code to provide these functions.
    #   e.g.: from simplejson import dumps, loads, ...
    from embci.utils import (                                      # noqa: W611
        # jsonify/unjsonify method
        dumps, loads,

        # convert string to bytes and unicode, py 2 & 3 compatiable
        #   e.g. ensure_bytes(u'\u963f') => b'\xe9\x98\xbf'
        ensure_bytes, ensure_unicode,

        # resolve arguments of a function
        #   e.g. sum(x, y=None, z=1) => (['x', 'y', 'z'], (None, 1, ))
        get_func_args,

        # create logging.Logger
        config_logger,

        # a property only computed once and becomes a constant attribute
        CachedProperty,
    )

    dumps = functools.partial(dumps, indent=None, separators=(',', ':'))
    params_types = (tuple, list, dict)

    logger_rpc = config_logger(
        'JSONRPC', level='DEBUG', format='[%(asctime)s] %(name)s %(message)s',
        datefmt='%Y%m%d-%H:%M:%S')
    logger_server = config_logger(
        'RPCServer', level='DEBUG', format='%(message)s')
    logger_rpc.setLevel('INFO')      # default be quiet
    logger_server.setLevel('DEBUG')  # default be verbose
    del config_logger

    namespace = dict(
        # utilities
        debug = lambda v=True: logger_rpc.setLevel('DEBUG' if v else 'INFO'),
        typename = lambda obj: type(obj).__name__,
        random_id = lambda length=8: ''.join([
            random.choice(string.ascii_lowercase+string.digits)
            for _ in range(length)
        ]),
        list_public_methods = lambda obj: [
            method for method in dir(obj)
            if not method.startswith('_') and callable(getattr(obj, method))
        ],
        resolve_dotted_attribute = lambda obj, attr, allow=True: reduce(
            getattr, [
                i for i in (attr.split('.') if allow else [attr])
                if not i.startswith('_')
            ], obj
        ),

        # modules, functions and instances
        **locals()
    )
    import types
    module = types.ModuleType(
        __name__ + '.external',
        'Virtual module that defines necessary external modules and functions')
    for _ in ['random', 'string', ]:
        namespace.pop(_, None)
    module.__dict__.update(namespace)
    return module


ext = __external__()  # This function can only be executed once


__codemap__ = {
    -32700: 'Parse Error',
    -32600: 'Invalid Request',
    -32601: 'Method Not Found',
    -32602: 'Invalid Params',
    -32603: 'Internal Error',
    -32500: 'Application Error',
    -32400: 'System Error',
    -32300: 'Transport Error',
    -32000: 'Server Error',
}


class ObjectRequest(dict):
    def __repr__(self):
        return '<Request {}>'.format(dict.__repr__(self))


class ObjectResponse(dict):
    def __repr__(self):
        return '<Response {}>'.format(dict.__repr__(self))


class ObjectError(dict):
    def __repr__(self):
        return '<Response(Error) {}>'.format(dict.__repr__(self))


class Fault(Exception):
    def __init__(self, code=-32000, message='', rpcid=None, **k):
        '''
        Parameters
        ----------
        code : int
            See __codemap__ for details.
        msg : string
            Procide short description of the error.
        rpcid : string | int, optional
        '''
        self.rpcid = rpcid
        if isinstance(code, ext.string_types) and not message:
            code, message = -32000, code
        self.code = int(code)
        self.codename = __codemap__.get(self.code, 'Server Error')
        self.message = \
            str(message).strip(' .') + \
            (k and '. (%s)' % str(k).strip('()[]{}') or '')
        if self.rpcid is not None:
            self.args = (self.rpcid, self.code, self.codename, self.message)
        else:
            self.args = (self.code, self.codename, self.message)

    def __repr__(self):
        return '<Fault{id} {code}: {codename} - {message}>'.format(
            id='' if self.rpcid is None else '(ID={})'.format(self.rpcid),
            **self.__dict__)


# =============================================================================
# Package layer: Payload, History

class Payload(object):
    version = 2.0

    @classmethod
    def config(cls, rpcid=None, version=None, **k):
        '''
        Safe entry: RPC Version and Request ID are checked and updated.
        Otherwise, Version & ID should be explictly specified when
        calling :func:Payload.make_resquest and :func:Payload.make_response.
        '''
        k.setdefault('rpcid', rpcid or ext.random_id())
        k.setdefault('version', version or cls.version)
        if cls.version != k['version']:
            return cls._for_version(**k)
        return cls

    @classmethod
    def _for_version(cls, version, **k):
        '''
        Constructor __init__ is not used in :class:Payload, so save
        the parameters directly to the class by creating a new class.
        '''
        return type(cls.__name__, (cls, ), {'version': version})

    @classmethod
    def check_request(cls, obj, *a, **k):
        '''
        RPC 1.0 Request Object
        ----------------------
        method: MUST be string
        params: MAY be omiited
            only support array (positional param)
        id : MUST be string | number | null(notifiaction)

        RPC 2.0 Request Object
        ----------------------
        jsonrpc : MUST be exactly "2.0"
        method : MUST be string
        params : MAY be omitted
            support both array (positional param) and object (keyword param)
        id : MUST be string | number | null(discouraged) or MAY be omiited
        '''
        try:
            obj    = ObjectRequest(obj)
            rpcid  = obj.get('id', 'noexist')
            method = obj.get('method')
            params = obj.get('params', [])
        except (TypeError, ValueError):
            raise Fault(-32600, 'type cannot be `%s`' % ext.typename(obj))
        except Exception as e:
            raise Fault(
                -32700, 'invalid json `%s`' % obj, **{ext.typename(e): str(e)})
        if 'jsonrpc' not in obj and rpcid == 'noexist':
            raise Fault(-32600, 'must contain RPC version or ID')
        if 'jsonrpc' in obj and rpcid is None:
            import warnings
            warnings.warn(
                'The use of Null(JSON) / None(Python) as a value for RPC ID '
                'is discouraged because of compatiablity for RPC 1.0 & 2.0')
        if not isinstance(method, ext.string_types):
            raise Fault(-32600, 'method must be string', rpcid)
        if not isinstance(params, ext.params_types):
            raise Fault(-32602, 'invalid `%s`' % ext.typename(params), rpcid)
        return obj

    @classmethod
    def make_request(cls, method, params=[], rpcid=None, notify=None, *a, **k):
        obj = ObjectRequest(method=method)
        if cls.version > 1:
            obj['jsonrpc'] = str(cls.version)
        if params:
            obj['params'] = params
        # RPC 2.0 Notification: ID MUST NOT exist
        # RPC 1.0 Notification: ID MUST be Null/None
        if not notify:
            obj['id'] = rpcid or ext.random_id()
        elif cls.version < 2:
            obj['id'] = None
        return cls.check_request(obj)

    @classmethod
    def check_response(cls, obj, reqid=None, *a, **k):
        '''
        RPC 1.0 Response Object
        -----------------------
        result : MUST be object | null(in case of invoking error)
        error :  MUST be null | object(in case of invoking error)
        id : MUST be the same ID as request's

        RPC 2.0 Response Object
        -----------------------
        jsonrpc : MUST be exactly "2.0"
        result : MUST NOT exist if error and REQUIRED on success
        error : MUST NOT exist on success and REQUIRES if error
        id : MUST be None | the same ID as request's

        Error Object
        ------------
        code : MUST be integer
        messaage : MUST be string
        data : MAY be omitted

        Possible Response Table
        -----------------------
        +--------+-------+---------+---------+
        | result | error | RPC 2.0 | RPC 1.0 |
        +--------+-------+---------+---------+
        | no     | no    | False   | False   |
        | no     | None  | False   | False   |
        | no     | value | True    | False   |
        | None   | no    | True    | False   |
        | None   | None  | False   | True    |
        | None   | value | False   | True    |
        | value  | no    | True    | False   |
        | value  | None  | False   | True    |
        | value  | value | False   | False   |
        +--------+-------+---------+---------+
        '''
        try:
            obj = ObjectResponse(obj)
            result = obj.get('result', 'noexist')  # noexist | None | value
            error = obj.get('error', 'noexist')    # noexist | None | value
            rpcid = obj.get('id', 'noexits')
        except (TypeError, ValueError):
            raise TypeError('invalid response `{}`'.format(obj))
        if cls.version < 2:
            assert 'noexist' not in [result, error], 'Result &Error MUST exist'
            assert not (None not in [result, error]), 'Invalid coexistance'
        else:
            assert 'noexist' in [result, error], 'Invalid coexistance'
            assert not (result == 'noexist' and not error), 'Invalid Error'
            assert obj['jsonrpc'] == str(cls.version), 'MUST specify version'
            assert rpcid != 'noexist', 'ID MUST exist'
        if reqid is not None:
            assert rpcid == reqid, 'ID MUST be the same as request\'s'
        if error not in ['noexist', None]:
            assert 'code' in error and 'message' in error, 'Invalid Error'
            assert isinstance(error['code'], int), 'code MUST be an integer'
            assert isinstance(error['message'], ext.string_types), \
                'message MUST be string'
            return ObjectError(obj)
        return obj

    @classmethod
    def make_response(cls, result, rpcid=None, *a, **k):
        obj = ObjectResponse(result=result, id=rpcid)
        if cls.version > 1:
            obj['jsonrpc'] = str(cls.version)
        else:
            obj['error'] = None
        return cls.check_response(obj)

    @classmethod
    def error(cls, fault, *a, **k):
        '''
        Convert error (instance of Fault or code & message) to response object

        Parameters
        ----------
        fault: Fault | int
            Can be instance of :class:Fault or code integer.
        msg : string
            Procide short description of the error.
        rpcid : string | int, optional
        '''
        if not isinstance(fault, Fault):
            fault = Fault(fault, *a, **k)
        obj = cls.make_response(None, k.get('rpcid', fault.rpcid))
        if cls.version > 1:
            obj.pop('result', None)
        obj['error'] = {'code': fault.code, 'message': fault.message}
        return cls.check_response(obj)


class History(object):
    requests = []
    responses = []

    def add_response(self, response):
        self.responses.append(response)

    def add_request(self, request):
        self.requests.append(request)

    @property
    def response(self):
        return self.responses and self.responses[-1] or None

    @property
    def request(self):
        return self.requests and self.requests[-1] or None

    def clear(self):
        del self.requests[:], self.responses[:]

    def __repr__(self):
        return '<History %s at 0x%x>' % (
            'TODO: list of reqs and reps', id(self))


History = History()


# =============================================================================
# Dispatch layer: JSONRPCDispatcher

class JSONRPCDispatcher(ext.xmlrpc_server.SimpleXMLRPCDispatcher):
    '''
    A dispatcher is used to handle RPC requests and generate response.
    In this layer, request(object) comes in and response(object) output.
    '''
    def __init__(self, encoding='utf8', *a, **k):
        self._uuid = ext.random_id(16)
        self._funcs = {}
        self._instance = None
        self.encoding = encoding

    def __repr__(self):
        return '<JSONRPCDispatcher %s at 0x%x>' % (self._uuid, id(self))

    def _get_method(self, method):
        '''
        Find by method name and return callable object or None (if not found).
        '''
        if method in self._funcs:
            return self._funcs[method]
        if self._instance is None:
            return
        try:
            func = ext.resolve_dotted_attribute(
                self._instance, method, True)
        except AttributeError:
            return
        else:
            return func

    def _dispatch(self, request, *a, **k):
        '''
        Dispatches the JSON-RPC method.

        JSON-RPC calls are forwarded to a registered function that
        matches the calles JSON-RPC method name, If no such function
        exist then the call is forwarded to the registered instance,
        if available.

        If the registered instance has a _dispatch method then that
        method will be called with the name of the JSON-RPC method and
        its parameters as a tuple, e.g. instance._dispatch('add',(2,3)).

        If the registered instance does not have a _dispatch method
        then the instance will be searched to find a matching method
        and, if found, will be called.

        Methods beginning with an '_' are considered private and will
        not be called.
        '''
        method = request.get('method')
        params = request.get('params', [])
        rpcid  = request.get('id')
        func   = self._get_method(method)
        if func is None:
            if hasattr(self._instance, '_dispatch'):
                return self._instance._dispatch(request)
            raise Fault(-32601, '`%s`' % method, rpcid)
        try:
            if isinstance(params, (tuple, list)):
                result = func(*params)
            elif isinstance(params, dict):
                if 'args' in params and 'kwargs' in params:
                    result = func(*params['args'], **params['kwargs'])
                else:
                    result = func(**params)
        except Fault as fault:
            fault.rpcid = rpcid
            raise fault
        except Exception as e:
            raise Fault(-32603, '%s: %s' % (ext.typename(e), e), rpcid)
        return result

    def _marshaled_dispatch(self, data, *a, **k):
        '''
        Dispatches an JSON-RPC method from marshaled (json) data.

        JSON-RPC methods are dispatched from the marshaled (json) data
        using the _dispatch method and the result is returned as
        marshaled data. For backwards compatibility, a dispatch
        function can be provided as an argument (see comment in
        JSONRPCRequestHandler.do_POST) but overriding the
        existing method through subclassing is the preferred means
        of changing method dispatch behavior.
        '''
        try:
            # decode string into request object[s]
            ext.logger_rpc.debug('--> %s' % data)
            requests = ext.loads(data)  # {...} | [...] | [{...} ...]
        except Exception as e:
            return ext.dumps(Payload.error(
                -32700, 'invalid json `%s`' % data, **{ext.typename(e): str(e)}
            ))

        # empty array (MultiCall i.e. list) or empty object (dict)
        if not requests:
            return ext.dumps(Payload.error(Fault(-32600, 'no request data')))
        if isinstance(requests, (tuple, )):
            requests = list(requests)
        elif not isinstance(requests, list):
            requests = [requests]   # [{...} ...]

        responses = []
        for request in requests:
            try:
                # validate Request Object using Payload and dispatch it
                request = Payload.check_request(request)
                result = self._dispatch(request)
                # skip return Response Object if the request is a notification
                rpcid = request.get('id')
                if rpcid is None:
                    continue
                response = Payload.make_response(result, rpcid)
            except Fault as fault:
                response = Payload.error(fault)
            except Exception as e:
                response = Payload.error(
                    -32400, '%s: %s' % (ext.typename(e), e))
            responses.append(response)
        if not responses:
            return ''
        rst = ext.dumps(responses if len(responses) > 1 else responses[0])
        ext.logger_rpc.debug('<-- %s' % rst)
        return rst

    handle_rpc = _marshaled_dispatch  # alias

    def system_describe(self):
        funcs = []
        for method in self.system_listMethods():
            func = self._get_method(method)
            if func is None:
                continue
            args = ext.get_func_args(func)[0]
            funcs.append({'name': method, 'params': args})
        return {
            'jsonrpc': Payload.version,
            'name': repr(self),
            'id': self._uuid,
            'procs': funcs,
        }

    def system_listMethods(self):
        '''
        system.listMethods() => ['add', 'subtract', 'multiple']

        Returns a list of the methods supported by the dispatcher.
        '''
        methods = set(self._funcs.keys())
        if self._instance is not None:
            if hasattr(self._instance, '_listMethods'):
                methods.update(self._instance._listMethods())
            elif not hasattr(self._instance, '_dispatch'):
                methods.update(ext.list_public_methods(self._instance))
        return sorted(methods)

    def system_methodHelp(self, method):
        '''
        system.methodHelp('add') => "Adds two integers together"

        Returns a string containing documentation for the specified method.
        '''
        func = self._get_method(method)
        if func is None:
            raise Fault(-32601, method)
        import pydoc
        return pydoc.getdoc(func)

    def system_methodSignature(self, method):
        '''
        system.methodSignature('add') => [double, int, int]

        Returns a list describing the signature of the method. In the
        above example, the add method takes two integers as arguments
        and returns a double result.
        '''
        func = self._get_method(method)
        if func is None:
            raise Fault(-32601, method)
        return ext.get_func_args(func)[0]

    def register_function(self, func, name=None):
        '''
        Registers a function to respond to JSON-RPC requests. The optional
        name argument can be used to set a Unicode name for the function.
        '''
        self._funcs[name or func.__name__] = func

    def register_instance(self, instance):
        '''
        Registers an instance to respond to JSON-RPC requests.

        Only one instance can be installed at a time.

        If the registered instance has a _dispatch method then that
        method will be called with the name of the JSON-RPC method and
        its parameters as a tuple
        e.g. instance._dispatch('add', (2, 3))

        If the registered instance does not have a _dispatch method
        then the instance will be searched to find a matching method
        and, if found, will be called. Methods beginning with an '_'
        are considered private and will not be called.

        If a registered function matches a JSON-RPC request, then it
        will be called instead of the registered instance.

        If the optional allow_dotted_names argument is true and the
        instance does not have a _dispatch method, method names
        containing dots are supported and resolved, as long as none of
        the name segments start with an '_'.

        *** SECURITY WARNING: **
        Enabling the allow_dotted_names options allows intruders
        to access your module's global variables and may allow
        intruders to execute arbitrary code on your machine.  Only
        use this option on a secure, closed network.
        '''
        self._instance = instance

    def register_introspection_functions(self):
        '''
        Registers the JSON-RPC introspection methods in the system namespace.
        See http://xmlrpc.usefulinc.com/doc/reserved.html.
        '''
        self.register_function(self.system_describe,    'system.describe')
        self.register_function(self.system_listMethods, 'system.listMethods')
        self.register_function(self.system_methodHelp,  'system.methodHelp')
        self.register_function(
            self.system_methodSignature, 'system.methodSignature')


# =============================================================================
# Send/Receive layer:
#     server side: JSONRPCServer, JSONRPCRequestHandler
#     client side: JSONRPCClient(aka. ServerProxy), Transport, SafeTransport

class JSONRPCRequestHandler(ext.xmlrpc_server.SimpleXMLRPCRequestHandler):
    '''
    JSON-RPC request handler class. Handles all HTTP POST requests and
    attempts to decode them as JSON-RPC requests.
    '''
    def do_POST(self):
        if self.path not in getattr(self, 'rpc_paths', [self.path]):
            return self.report_404()  # return None
        try:
            max_chunk_size = 10 * 1024 * 1024
            size_remaining = int(self.headers['content-length'])
            data = ''
            while size_remaining:
                string = self.rfile.read(min(size_remaining, max_chunk_size))
                data += string; size_remaining -= len(string)      # noqa: E702
            response = self.server._marshaled_dispatch(data)
            self.send_response(200)
        except Exception as e:
            response = ext.dumps(Payload.error(Fault(
                -32603, '%s: %s' % (ext.typename(e), e))))
            self.send_response(500)
        if not isinstance(response, bytes):  # py 2 & 3
            response = response.encode('utf8')
        self.send_header('Content-type', 'application/json-rpc')
        self.send_header('Content-length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_request(self, code='-', size='-'):
        from six.moves import BaseHTTPServer
        BaseHTTPServer.BaseHTTPRequestHandler.log_request(self, code, size)

    def log_error(self, format, *args):
        '''Overload :method: BaseHTTPRequestHandler.log_error'''
        self.log_message(format, *args, level=30)

    def log_message(self, format, *args, **kwargs):
        '''Overload :method: BaseHTTPRequestHandler.log_message'''
        ext.logger_server.log(
            kwargs.get('level', 10),
            '%s - - [%s] %s' % (
                self.client_address[0],
                self.log_date_time_string(),
                format % args))


class JSONRPCServer(ext.socketserver.TCPServer, JSONRPCDispatcher):
    allow_reuse_address = True

    def __init__(self, addr, requestHandler=JSONRPCRequestHandler,
                 logRequests=False, encoding=None, bind_and_activate=True):
        JSONRPCDispatcher.__init__(self, encoding or 'utf8')
        ext.socketserver.TCPServer.__init__(
            self, addr, requestHandler, bind_and_activate)
        ext.logger_server.setLevel('DEBUG' if logRequests else 'INFO')
        import fcntl
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

    def __repr__(self):
        return '<JSONRPCServer %s at 0x%x>' % (self._uuid, id(self))


class _TransportMixIn(object):
    '''Just extends the XML-RPC transport where necessary.'''
    user_agent = 'jsonrpc by EmBCI (Python%s)' % '.'.join(
        map(str, ext.sys.version_info[:3]))

    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "application/json-rpc")
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    class _JSONParser(object):
        def __init__(self, target):
            # self.feed = lambda data: target.write(ext.ensure_unicode(data))
            self.feed = lambda data: target.write(data.decode('utf8'))
            self.close = lambda *a: None

    class _JSONTarget(ext.StringIO, object):
        def close(self):
            self.flush()
            data = self.getvalue()
            ext.StringIO.close(self)
            return data

    def getparser(self):
        '''
        getparser() -> parser, unmarsaller

        XML-RPC need this interface to parse string into XML object.
        But in JSON-RPC, it is not necessary.
        '''
        target = self.__class__._JSONTarget()
        return self.__class__._JSONParser(target), target


class JSONRPCTransport(_TransportMixIn, ext.xmlrpc_client.Transport):
    __init__ = ext.xmlrpc_client.Transport.__init__


class JSONRPCSafeTransport(_TransportMixIn, ext.xmlrpc_client.SafeTransport):
    __init__ = ext.xmlrpc_client.SafeTransport.__init__


class _Method(object):
    def __init__(self, send, method):
        self.__send, self.__method = send, method

    def __getattr__(self, method):
        return _Method(self.__send, '%s.%s' % (self.__method, method))

    def __call__(self, *args, **kwargs):
        return self.__send(self.__method, *args, **kwargs)

    def __repr__(self):
        return '<Method `%s`>' % self.__method


class JSONRPCClient(ext.xmlrpc_client.ServerProxy):
    def __init__(self, uri, transport=None, encoding=None,
                 verbose=0, version=None):
        schema, host, path, query, tag = ext.urllib.parse.urlsplit(uri)
        if schema not in ('http', 'https'):
            raise IOError('Unsupported JSON-RPC protocol.')
        self.__host, self.__handler = host, path
        if transport is None:
            if schema == 'https':
                transport = JSONRPCSafeTransport()
            else:
                transport = JSONRPCTransport()
        self.__transport = transport
        self.__encoding = encoding
        self.__verbose = verbose

    @ext.CachedProperty
    def _notify(self):
        func = ext.functools.partial(self._config_request, notify=True)
        return type('_Notify', (object, ), {
            '__getattr__': lambda obj, name: _Method(func, name),
            '__repr__': lambda self: '<NotificationProxy at 0x%x>' % id(self)
        })()

    @ext.CachedProperty
    def _multicall(self):
        return JSONRPCMultiCall(self)

    # Python 3 only: default value for keyword argument after varargs
    # def _config_request(self, method, *a, rpcid=None, notify=False, **k)
    def _config_request(self, method, *a, **k):
        '''
        - Support positional, keyword arguments and both at same time.
        - Support mark request as notification at runtime.

        Provide an argument namespace for basic request configuration.
        If keyword argument `notify` is specified, it will be collected
        into local variable `notify`. If other parameter passing tricks
        like functools.partial are used, it will also work.
        '''
        notify = k.pop('notify', False)
        rpcid = k.pop('rpcid', None)
        if a and k:
            params = {'args': a, 'kwargs': k}
        else:
            params = k or a
        return self.__request(method, params, rpcid, notify)

    def __request(self, method, params, rpcid=None, notify=False):
        request_obj = Payload.make_request(method, params, rpcid, notify)
        History.add_request(request_obj)

        request = ext.ensure_bytes(ext.dumps(request_obj))
        response = self.__transport.request(
            self.__host, self.__handler, request, verbose=self.__verbose)
        if notify:
            return None
        try:
            response_obj = ext.loads(response)
        except (TypeError, ValueError):
            raise RuntimeError('Invalid response: `{}`'.format(response))

        History.add_response(response_obj)
        response_obj = Payload.check_response(response_obj, request_obj['id'])

        if response_obj.get('error'):
            raise Fault(**response_obj['error'])
        return response_obj['result']

    def __getattr__(self, name):
        if name[0] == name[-1] == '_':
            return None
        elif name.startswith('_'):
            raise AttributeError('Invalid method name')
        return _Method(self._config_request, name)

    def __dir__(self):
        return self.__dict__.keys()

    def __repr__(self):
        return '<JSONRPCClient %s%s at 0x%x>' % (
            self.__host, self.__handler, id(self))

    __str__ = __repr__


class _MultiCallMethod(object):
    def __init__(self, request_list, method):
        self.__list, self.__method = request_list, method

    def __getattr__(self, method):
        return _MultiCallMethod(self.__list, '%s.%s' % (self.__method, method))

    def __call__(self, *args, **kwargs):
        self.__list.append((self.__method, args, kwargs))

    def __repr__(self):
        return '<MultiCallMethod `%s`>' % self.__method


class JSONRPCMultiCall(object):
    def __init__(self, client):
        self.__client = client
        self.__job_list = []
        self.__notify_list = []

    @ext.CachedProperty
    def _notify(self):
        return type('_MultiCallNotify', (object, ), {
            '__getattr__': lambda obj, name: _MultiCallMethod(
                self.__notify_list, name),
            '__repr__': lambda self: '<NotificationProxy at 0x%x>' % id(self)
        })()

    def __call__(self, iterator=True):
        responses = []
        for method, a, k in self.__notify_list:
            k.setdefault('notify', True)
            self.__client._config_request(method, *a, **k)
        for method, a, k in self.__job_list:
            try:
                response = self.__client._config_request(method, *a, **k)
            except Exception as e:
                response = e
            responses.append(response)
        del self.__notify_list[:], self.__job_list[:]
        return iter(responses) if iterator else responses

    def __getattr__(self, name):
        if name[0] == name[-1] == '_':
            return None
        elif name.startswith('_'):
            raise AttributeError('Invalid method name')
        return _MultiCallMethod(self.__job_list, name)

    def __repr__(self):
        return '<JSONRPCMultiCall on %s>' % self.__client


# =============================================================================
# Exports

__all__ = ['History', 'Payload'] + [
    'JSONRPC' + _
    for _ in [
        'Server', 'Dispatcher', 'RequestHandler',
        'Client', 'Transport', 'SafeTransport', 'MultiCall',
    ]
]

# THE END
