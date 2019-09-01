#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/auth/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-05-25 03:05:43

import os

# requirements.txt: network: bottle, bottle-cork, beaker
import bottle
import cork
from beaker.middleware import SessionMiddleware

__basedir__ = os.path.dirname(os.path.abspath(__file__))
__auth__ = os.path.join(__basedir__, 'secret')
__index__ = os.path.join(__basedir__, 'index.html')
__admin__ = os.path.join(__basedir__, 'admin.html')
__login__ = os.path.join(__basedir__, 'login.html')
__reset_html__ = os.path.join(__basedir__, 'reset_password.html')
__reset_email__ = os.path.join(__basedir__, 'reset_email.html')
__register_email__ = os.path.join(__basedir__, 'register_email.html')

try:
    with open(os.path.join(__basedir__, 'README.md')) as _:
        __doc__ = _.read()
except Exception:
    __doc__ = ''

app = bottle.Bottle()
auth = cork.Cork(__auth__, email_sender='hankso1106@gmail.com')
admin_only = auth.make_auth_decorator(
    role='admin',
    fail_redirect='/admin_only',
)
authorize = auth.make_auth_decorator(
    role='user',
    fail_redirect='/login',
)


def GETD(key=None, default=None):
    #  d = bottle.request.params
    d = bottle.request.query
    if key is not None:
        return d.getunicode(key, default)
    return d


def POSTD(key=None, default=None):
    #  d = bottle.request.params
    d = bottle.request.forms
    if key is not None:
        return d.getunicode(key, default)
    return d


def FILED(key=None, default=None):
    d = bottle.request.files
    if key is not None:
        return d.getunicode(key, default)
    return d


@app.get('/')
@bottle.view(__index__)
def auth_index():
    auth.require(fail_redirect='/login')


@app.get('/login')
@bottle.view(__login__)
def auth_login_form():
    pass


@app.post('/login')
def auth_login():
    if POSTD('remember') == 'on':
        pass  # TODO: long time cache
    auth.login(
        POSTD('username'), POSTD('password'),
        success_redirect='/',
        fail_redirect='/login',
    )


@app.get('/logout')
def auth_logout():
    auth.logout(success_redirect='/login')


@app.post('/register')
def auth_register():
    auth.register(
        POSTD().username, POSTD().password, POSTD().email,
        email_template=__register_email__,
        base_url='http://10.0.0.1/apps/auth/register/'
    )
    return 'Registration confirmation sent. Please check your mailbox.'


@app.get('/register/:code')
def auth_register_check(code):
    auth.validate_registration(code)


@app.get('/reset_password')
def auth_reset_password_request():
    '''
    Step One: Request to reset user's password. Auth robot will send a email
    to your mailbox which contain the link to reset password form.
    '''
    auth.send_password_reset_email(
        POSTD().username, POSTD().email,
        email_template=__reset_email__,
        base_url="http://10.0.0.1/apps/auth/reset_password"
    )
    return 'Confirmation email has been sent. Please check your mailbox.'


@app.get('/reset_password/:code')
@bottle.view(__reset_html__)
def auth_reset_password_form(code):
    '''
    Step Two: Copy your unique `reset_code` (like a token) from URL to
    forms in HTML, where you can input your new password.
    '''
    return {'reset_code': code}


@app.post('/reset_password')
def auth_reset_password_check():
    '''
    Step Three: POST your form data here to update your password.
    Reset code should be validated before password reset.
    '''
    auth.reset_password(POSTD().reset_code, POSTD().password)
    bottle.redirect('/login')


# =============================================================================
# Administration
#
@app.get('/admin')
@bottle.view(__admin__)
@admin_only
def auth_admin():
    return {
        'me': auth.current_user,
        'users': auth_manage_users('list'),
        'roles': auth_manage_roles('list'),
    }


@app.route('/admin_only')
def auth_admin_only():
    return '<p>Sorry. You are not authorized to perform this action.</p>'


@app.post('/<action>_role')
@admin_only
def auth_manage_roles(action):
    if action == 'create':
        auth.create_role(POSTD('role'), int(POSTD('level')))
    elif action == 'delete':
        auth.delete_role(POSTD('role'))
    elif action == 'reset':
        try:
            auth_manage_roles('delete')
        except Exception:
            pass
        auth_manage_roles('create')
    elif action == 'list':
        return dict(auth.list_roles())
    else:
        bottle.abort(500, 'Invalid action `{}`!'.format(action))


@app.post('/<action>_user')
@admin_only
def auth_manage_users(action):
    if action == 'create':
        auth.create_user(
            POSTD().username, POSTD().role, POSTD().password,
            POSTD().email, POSTD().desc
        )
    elif action == 'delete':
        auth.delete_user(POSTD().username)
    elif action == 'reset':
        # TODO: change password directly
        raise NotImplementedError
    elif action == 'list':
        return {
            user[0]: {'role': user[1], 'email': user[2], 'desc': user[3]}
            for user in auth.list_users()
        }
    else:
        bottle.abort(500, 'Invalid action `{}`!'.format(action))


application = SessionMiddleware(
    app, {
        'session.cookie_expires': True,
        'session.encrypt_key': 'asfd',
        'session.httponly': True,
        'session.timeout': 3600 * 24,
        'session.type': 'cookie',
        'session.validate_key': True,
    }
)
__all__ = ['application']
# THE END
