# cli.py
import os

import click
import pyperclip

from database_manager.models import FILE_USERS_DB, SQLAlchemyManager


@click.group()
@click.option('-a/-not-alias', help='print or not alias')
@click.option('-c/-not-category', help='print or not category')
@click.option('-u/-not-url', help='print or not url')
@click.pass_context
def cli(ctx, a, c, u):
    """
    Use "SOS [COMMAND] --help" for more information
    """
    ctx.obj = {
        'FLAGS': {
            'alias': a,
            'category': c,
            'url': u
        }
    }


user_argument = click.option('--user', '-u', prompt="Username", help="Provide your username",
                             default=lambda: os.environ.get('USERNAME'))
password_argument = click.option('--password', '-p', help="Provide your password",
                                 prompt=True, hide_input=True)


@cli.command()
@user_argument
@password_argument
def uadd(user, password):
    """
    add user command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB, user, password)

    if manager_obj.user_obj.check_user():
        print(f'Error: User named "{user}" already exists')
    else:
        manager_obj.user_obj.add_user(password)
        print(f'User named "{user}" created')


@cli.command()
@user_argument
@password_argument
@click.option('-l', '--newusername', prompt="NewUsername", help="Provide new username")
@click.option('-pl', '--password-for-newusername', prompt=False, hide_input=True)
def uupdate(user, password, newusername, password_for_newusername):
    """
    update username (and password) command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB, user, password)

    if not manager_obj.user_obj.check_user_password(password):
        print('Error: incorrect login or password')
        return

    if manager_obj.user_obj.check_user(newusername):
        print(f'Error: User named "{newusername}" already exists')
    else:
        manager_obj.user_obj.update_user(password, newusername, password_for_newusername)


@cli.command()
@user_argument
@password_argument
def udelete(user, password):
    """
    delete user command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB, user, password)

    if not manager_obj.user_obj.check_user_password(password):
        print('Error: incorrect login or password')
        return

    manager_obj.user_obj.del_user()
    print(f'User named "{user}" deleted')


@cli.command()
@click.pass_context
def ushow(ctx):
    """
    show users command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB)

    users = manager_obj.user_obj.all_users()
    for user in users:
        print(user)


@cli.command()
@user_argument
@password_argument
@click.option('-c', "--category", help='"default" for default category, '
                                       'skip for all logins, optional',
              default=None, required=False)
def show(user, password, category):
    """
    show logins command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB, user, password)

    if not manager_obj.user_obj.check_user_password(password):
        print('Error: incorrect login or password')
        return

    logins = manager_obj.unit_obj.get_logins(category)
    for login in logins:
        print(login)


@cli.command()
@user_argument
@password_argument
@click.option('-l', "--login", prompt="Login", help="Provide login")
def get(user, password, login):
    """
    get password by login command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB, user, password)

    if not manager_obj.user_obj.check_user_password(password):
        print('Error: incorrect login or password')
        return

    if manager_obj.unit_obj.check_login(login):
        pyperclip.copy(manager_obj.unit_obj.get_password(login))
        print(f'Password is placed on the clipboard')
    else:
        print(f'Error: login "{login}" not exists')


@cli.command()
@user_argument
@password_argument
@click.option('-l', "--login", prompt="Login", help="Provide login")
def delete(user, password, login):
    """
    delete login and password command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB, user, password)

    if not manager_obj.user_obj.check_user_password(password):
        print('Error: incorrect login or password')
        return

    if manager_obj.unit_obj.check_login(login):
        manager_obj.unit_obj.delete_unit(login)
        print(f' login "{login}" deleted')
    else:
        print(f'Error: login "{login}" not exists')


@cli.command()
@user_argument
@password_argument
@click.option('-l', "--login", prompt="Login", help="Provide login")
@click.option('-pl', '--password-for-login', prompt=True, help="Provide password for login", hide_input=True)
@click.option('-c', "--category", help='"default" or skip for default category, optional',
              default=None, required=False)
@click.option('-ur', "--url", help='url, optional', default=None, required=False)
@click.option('-a', "--alias", help='alias, optional', default=None, required=False)
def add(user, password, login, password_for_login, category, url, alias):
    """
    add login and password command
    """
    manager_obj = SQLAlchemyManager(FILE_USERS_DB, user, password)

    if not manager_obj.user_obj.check_user_password(password):
        print('Error: incorrect login or password')
        return

    if manager_obj.unit_obj.check_login(login):
        print(f'Error: login "{login}" already exists')
    else:
        category = None if category == 'default' else category
        manager_obj.unit_obj\
            .add_unit(login, password_for_login, category, url, alias)
        print(f' login "{login}" added')


if __name__ == '__main__':
    cli()
