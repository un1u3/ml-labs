from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
engine = create_engine('postgres+psycopg2///postgres:postgres@localhost:5432/tuta', echo = True)


meta = MetaData()

people = Table(
    "people",
    meta,
    Column('id', Integer, primary_key = True),
    Column('name', String),
    Column('age', Integer)


)