from sqlalchemy import create_engine
import cx_Oracle

host = '10.90.148.112'
port = '1521'
name = 'SIRPRDEU'
user= 'SIRVALREAD'
password = 'SIRVALREAD'
dsn = cx_Oracle.makedsn(host, port, service_name=name)

cstr_DK = 'oracle://SIRVALREAD_DK:SIRVALREAD_DK@{dsn}'.format(dsn=dsn)
cstr_SE = 'oracle://SIRVALREAD_SE:SIRVALREAD_SE@{dsn}'.format(dsn=dsn)
cstr_NO = 'oracle://SIRVALREAD_NO:SIRVALREAD_NO@{dsn}'.format(dsn=dsn)

engine_DK = create_engine(cstr_DK, convert_unicode=False, pool_recycle=10, pool_size=50, echo=True)
engine_SE = create_engine(cstr_SE, convert_unicode=False, pool_recycle=10, pool_size=50, echo=True)
engine_NO = create_engine(cstr_NO, convert_unicode=False, pool_recycle=10, pool_size=50, echo=True)
