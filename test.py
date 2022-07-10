import datetime
from dateutil.tz import tzlocal

a = datetime.datetime(2022, 7, 10, 13, 47, 36, tzinfo = tzlocal()).timestamp()
b = datetime.datetime.now().timestamp()

print(a)
print(b)
print(a>b)
print(b>a)
