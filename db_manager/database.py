from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from settings import FILE_DB, FILE_TEST_DB
from db_manager import models, schemas
from pydantic import ValidationError
from pathlib import Path
from typing import List, Any
from encryption_manager import models as enc_models


class DBManager:
    """Менеджер управления БД"""
    _model: models.Base = None
    _schema: schemas.BaseModel = None
    
    def __init__(self, model: models.Base, schema: schemas.BaseModel, prod_db=True):
        self._model = model
        self._schema = schema
        self.file_db: Path = FILE_DB if prod_db else FILE_TEST_DB
        self.file_db.touch()
        self.bd_url = f'sqlite:///{self.file_db}'
        engine = create_engine(self.bd_url, connect_args={"check_same_thread": False})
        models.Base.metadata.create_all(bind=engine)
        self.session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    @property
    def session(self):
        return self.session_local()
        
    def clear_db(self):
        """Закрытие сессии и удаление БД"""
        self.session.close()
        self.file_db.unlink()

    def get_objects(self, filters: dict) -> List[Any]:
        """Получить список объектов модели с учётом переданных фильтров"""
        return self.session.query(self._model).filter_by(**filters).all()

    def get_obj(self, filters: dict) -> Any:
        """Получить объект модели с учетом указанных фильтров"""
        return self.session.query(self._model).filter_by(**filters).first() 

    def create_obj(self, data: dict) -> bool:
        """Универсальный метод создания объекта в БД с 
        обязательной валидацией атрибутов до создания"""
        db = self.session
        try:
            schema_obj = self._schema(**data)
            new_obj = self._model(**schema_obj.dict())
            db.add(new_obj)
            db.commit()
            db.refresh(new_obj)
        except ValidationError:
            return False
        return True

    def update_objects(self, filters: dict, data: dict) -> bool:
        """Обновить данные моделей подпадающих под условия фильтрации
        на данные переданные в data"""
        db = self.session
        try:
            db.query(self._model).filter_by(**filters).update(
                data,
                synchronize_session='evaluate'
            )
            db.commit()
        except:
            return False
        return True

    def delete_objects(self, filters: dict) -> bool:
        """Удалить объекты из базы, которые подпадают под условия фильтрации"""
        db = self.session
        try:
            db.query(self._model).filter_by(**filters).delete(synchronize_session='evaluate')
            db.commit()
        except:
            return False
        return True

    def generate_hash(self, value: str) -> str:
        """Генерация хэш по переданному значению"""
        return enc_models.get_hash(value.encode("utf-8"))

    def __get_secret_obj(self, username: str, password: str):
        """Внутренний метод получения объекта шифровальщика"""
        _key = self.generate_hash(username + password)
        return enc_models.AESCipher(_key)

    def encrypt_value(self, username: str, password: str, raw: str) -> str:
        """Зашифровать по пользовательским данным текст raw"""
        _cipher = self.__get_secret_obj(username, password)
        return _cipher.encrypt(raw)

    def decrypt_value(self, username: str, password: str, enc: str) -> str:
        """Расшифровать по пользовательским данным ранее зашифрованный текст enc"""
        _cipher = self.__get_secret_obj(username, password)
        return _cipher.decrypt(enc)


class CategoryManager(DBManager):

    def __init__(self, prod_db=True) -> None:
        super().__init__(
            model=models.Category,
            schema=schemas.Category,
            prod_db=prod_db
        )


class UserManager(DBManager):

    def __init__(self, prod_db=True) -> None:
        super().__init__(
            model=models.User,
            schema=schemas.User,
            prod_db=prod_db
        )


class UnitManager(DBManager):

    def __init__(self, prod_db=True) -> None:
        super().__init__(
            model=models.Unit,
            schema=schemas.Unit,
            prod_db=prod_db
        )


class ProxyAction:
    """Класс основных действий через проксирование объектных менеджеров.
    Все методы класса Прокси будут работать с БД относительно предустановленных
    моделей и схем в соответствующих проксируемых менеджерах"""
    def __init__(self, manager: DBManager):
        """В качестве менеджера передаётся один из объектных менеджеров базы"""
        self._manager = manager

    @property
    def manager(self):
        """Обращение к проксируемому менеджеру"""
        return self._manager

    @manager.setter
    def manager(self, new_manager: DBManager) -> None:
        """Замена проксируемого менеджера через присваивание другого"""
        self._manager = new_manager

    def __check_manager(self, need_use_class: DBManager) -> bool:
        """Проверка текущего проксируемого менеджера на соответствие указанному"""
        if isinstance(self.manager, need_use_class):
            return True
        return False

    def check_obj(self, filters: dict) -> bool:
        """Проверяем наличие экземпляра модели по менеджеру в БД"""
        _obj = self.manager.get_obj(filters=filters)
        if isinstance(_obj, models.Base):
            return True
        return False
        
    def add_obj(self, data: dict) -> bool:
        """Создание новых объектов в БД через проксируемого менеджера.
        Не забывайте передавать для Units в data значения username и password,
        т.к. они используются для encrypt"""
        if self.__check_manager(UserManager):
            _new_user = self.manager._schema(**data)
            _data = _new_user.dict(include={"username", "password"})
            _value = ''.join([x for x in _data.values()])
            _new_user.password = self.manager.generate_hash(_value)
            data = _new_user.dict()
        if self.__check_manager(UnitManager):
            _username = data.pop('username')
            _password = data.pop('password')
            _new_unit = self.manager._schema(**data)
            _new_unit = self.manager.encrypt_value(
                username=_username, password=_password, raw=_new_unit.secret
            )
            data = _new_unit.dict()
        return self.manager.create_obj(data=data)        

    def update_obj(self, filters: dict, data: dict):
        """Обновление объектов по проксируемому менеджеру,
        удовлетворяющих условиям в filters, замена данных указанных в data"""
        return self.manager.update_objects(filters=filters, data=data)

    def delete_obj(self, filters: dict) -> bool:
        """Удаление объектов по проксируемому менеджеру,
        удовлетворяющих условиям в filters"""
        return self.manager.delete_objects(filters=filters)

    def check_user_password(self, username: str, password: str):
        """Проверка наличия пользователя с таким именем и паролем"""
        if self.__check_manager(UserManager):
            pass_hash = self.manager.generate_hash(username + password)
            _obj = self.manager.get_obj(filters={"username": username, "password": pass_hash})
            return True if _obj else False
        raise TypeError
        
    def get_secret(self, filters: dict) -> str:
        """Получить пароль из Unit'a.
        Не забывайте передавать в filters значения username и password,
        т.к. они используются для decrypt"""
        if not self.__check_manager(UnitManager):
            raise TypeError
        _username = filters.pop('username')
        _password = filters.pop('password')
        _obj = self.manager.get_obj(**filters)
        if not _obj:
            raise IndexError
        return self.manager.decrypt_value(
            username=_username, password=_password, enc=_obj.secret
        )
