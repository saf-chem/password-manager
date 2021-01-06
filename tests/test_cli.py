import unittest
import pathlib
from click.testing import CliRunner
from cli import cli
import database_manager.models as models_db


class TestCli(unittest.TestCase):
    _login_user = 'temp'
    _password_user = 'temp1234!@#$'
    _path_project = pathlib.Path.cwd() / 'tests'

    @classmethod
    def setUpClass(cls):
        """Инициация тестовой базы данных"""
        if pathlib.Path.exists(cls._path_project / 'test_users.sqlite'):
            pathlib.Path.unlink(cls._path_project / 'test_users.sqlite')
        # инициация runner через которого будем обращаться к cli
        cls.runner = CliRunner()
        # ручная проверка и создание тестовых директорий с тестовыми БД
        if not pathlib.Path.exists(cls._path_project):
            pathlib.Path.mkdir(cls._path_project)   
        # создание тестовой БД пользователей
        cls._file_user_db = cls._path_project / 'test_users.sqlite'
        # инициация менеджера управления тестовыми БД
        cls._test_BD = models_db.SQLAlchemyManager(
            file_db=cls._file_user_db, user=cls._login_user
        )        

    @classmethod
    def tearDownClass(cls):
        """Очистка сгенерированных тестовых данных"""
        # pathlib.Path.unlink(cls._path_project / 'test_users.sqlite')
        pass

    
    def test_uadd(self):
        """
        Test uadd command
        """
        # Вызываем cli
        result = self.runner.invoke(
            cli,
            [
                'uadd',  # Команда
                '-u', self._login_user,  # Первая опция
                '-p', self._password_user,  # Вторая опция
                '--db', self._file_user_db
            ]
        )

        self.assertEqual(result.exit_code, 0)  # Проверяем код возврата
        self.assertEqual(result.output, f'User named "{self._login_user}" created\n')  # Проверяем сообщение
        # об успешности создания пользователя

        # Проверяем cli при вводе с подсказками (можно посмотреть, как ниже  print(result.output) )
        result = self.runner.invoke(cli, input=f'{self._login_user}\n{self._password_user}\n',  # Опции. Построчно
                                    args=['uadd', '--db', self._file_user_db])  # Команда

        self.assertNotEqual(result.exit_code, 0)  # Пользователь уже есть, поэтому код возврата не 0
        # Нужно всем неуспешным завершениям проставить exit(-1), как в этом коммите
        res_str = result.output.split('\n')  # Делим вывод построчно
        self.assertEqual(res_str[-2], f'Error: User named "{self._login_user}" already exists') # Проверяем нижнюю
        # строку на соответсвии тексту ошибки

