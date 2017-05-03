from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine, and_, or_     # noqa
from sqlalchemy.orm.exc import NoResultFound

Base = declarative_base()


class Host(Base):
    __tablename__ = 'host'
    id = Column(Integer, primary_key=True)
    ipv4 = Column(String(16), nullable=False, unique=True)
    hostname = Column(String(250), nullable=False)
    comment = Column(String(250))

    services = relationship("Service", order_by="Service.id", cascade='delete')


class Service(Base):
    __tablename__ = 'service'
    id = Column(Integer, primary_key=True)
    port = Column(Integer, nullable=False)
    proto = Column(String(3), nullable=False)
    service = Column(String(20), nullable=False)
    state = Column(String(250), nullable=False)
    version = Column(String(250))
    host_id = Column(Integer, ForeignKey('host.id'))
    host = relationship(Host)

    UniqueConstraint('host_id', 'port', name='host_port')


class Database(object):
    def __init__(self, database='sqlite:///pysploit.db'):
        engine = create_engine(database)

        Base.metadata.create_all(engine)
        Base.metadata.bind = engine
        DBSession = sessionmaker(bind=engine)
        self.session = DBSession()

    def _filter(self, model, filters):
        res = self.session.query(model)
        res = res.filter(filters)
        return res

    def filter(self, model, filters):
        res = self._filter(model, filters)
        return res.all()

    def get(self, model, filters):
        res = self._filter(model, filters)
        return res.one()

    def create(self, model, commit=True, **kwargs):
        new_obj = model(**kwargs)
        self.session.add(new_obj)
        if commit is True:
            self.session.commit()
        return new_obj

    def delete(self, model, filters):
        res = self._filter(model, filters)
        return res.delete()

    def get_or_create(self, model, filters):
        try:
            return self.get(model, filters)
        except NoResultFound:
            return self.create(model, filters)
