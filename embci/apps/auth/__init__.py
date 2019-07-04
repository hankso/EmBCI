#!/usr/bin/env python
# coding=utf-8
#
# File: auth/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sat 25 May 2019 03:05:43 CST

''''''

import os

# requirements.txt: network: bottle, bottle-cork
import bottle
import cork
from beaker.middleware import SessionMiddleware

__dir__ = os.path.dirname(os.path.abspath(__file__))
__auth__ = os.path.join(__dir__, 'secret')
__index__ = os.path.join(__dir__, 'index.html')
__admin__ = os.path.join(__dir__, 'admin.html')
__login__ = os.path.join(__dir__, 'login.html')
__reset_html__ = os.path.join(__dir__, 'reset_password.html')
__reset_email__ = os.path.join(__dir__, 'reset_email.html')
__register_email__ = os.path.join(__dir__, 'register_email.html')

try:
    with open(os.path.join(__dir__, 'README.md')) as _:
        __doc__ = HELP = _.read()
except Exception:
    HELP = ''

application = bottle.Bottle()
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


@bottle.get('/')
@bottle.view(__index__)
def auth_index():
    auth.require(fail_redirect='/login')


@bottle.get('/login')
@bottle.view(__login__)
def auth_login_form():
    pass


@bottle.post('/login')
def auth_login():
    if POSTD('remember') == 'on':
        pass  # TODO: long time cache
    auth.login(
        POSTD('username'), POSTD('password'),
        success_redirect='/',
        fail_redirect='/login',
    )


@bottle.get('/logout')
def auth_logout():
    auth.logout(success_redirect='/login')


@bottle.post('/register')
def auth_register():
    auth.register(
        POSTD().username, POSTD().password, POSTD().email,
        email_template=__register_email__,
        base_url='http://10.0.0.1/apps/auth/register/'
    )
    return 'Registration confirmation sent. Please check your mailbox.'


@bottle.get('/register/:code')
def auth_register_check(code):
    auth.validate_registration(code)


@bottle.get('/reset_password')
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


@bottle.get('/reset_password/:code')
@bottle.view(__reset_html__)
def auth_reset_password_form(code):
    '''
    Step Two: Copy your unique `reset_code` (like a token) from URL to
    forms in HTML, where you can input your new password.
    '''
    return {'reset_code': code}


@bottle.post('/reset_password')
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
@bottle.get('/admin')
@bottle.view(__admin__)
@admin_only
def auth_admin():
    return {
        'me': auth.current_user,
        'users': auth_manage_users('list'),
        'roles': auth_manage_roles('list'),
    }


@bottle.route('/admin_only')
def auth_admin_only():
    return '<p>Sorry. You are not authorized to perform this action.</p>'


@bottle.post('/<action>_role')
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


@bottle.post('/<action>_user')
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


# offer application object for Apache2 and embci.webui
application = SessionMiddleware(
    application, {
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
