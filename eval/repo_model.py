from peewee import SqliteDatabase, Model, CharField, IntegerField, BooleanField, DateField

db_filename = 'repos.db'

db = SqliteDatabase(db_filename)


class Repo(Model):
    id_ = CharField(primary_key=True)
    url = CharField(null=True)
    star = IntegerField(null=True)
    archived = BooleanField(null=True)
    pushedDate = DateField(null=True)

    class Meta:
        database = db
