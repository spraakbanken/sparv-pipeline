# -*- coding: utf-8 -*-

import os
from . import system
from . import log
from . import constants

# Max size of SQL statement
MAX_ALLOWED_PACKET = 900000


class MySQL(object):
    binaries = ('mysql', 'mysql5')

    def __init__(self, database, username=None, password=None, encoding="UTF-8", output="", append=False):
        self.arguments = [database]
        if username:
            self.arguments += ['-u', username]
        if password:
            self.arguments += ['-p', password]
        self.encoding = encoding
        self.output = output
        self.first_output = True
        if self.output and not append:
            if os.path.exists(self.output):
                os.remove(self.output)

    def execute(self, sql, *args):
        if self.first_output:
            if sql.strip():
                sql = "SET @@session.long_query_time = 1000;\n" + sql
            self.first_output = False
        if self.output:
            # Write SQL statement to file
            with open(self.output, "a", encoding=self.encoding) as outfile:
                outfile.write(sql + "\n")
        else:
            # Execute SQL statement
            out, err = system.call_binary(self.binaries[0], self.arguments, sql % args,
                                          binary_names=self.binaries, encoding=self.encoding)
            if out:
                log.info("MySQL: %s", out)
            if err:
                log.error("MySQL: %s", err)
        # return out

    def create_table(self, table, drop, columns, primary=None, indexes=None, constraints=None, **kwargs):
        sqlcolumns = [u"  %s %s %s DEFAULT %s" %
                      (_ATOM(name), _TYPE(typ), extra or "", _VALUE(default))
                      for name, typ, default, extra in columns]
        if primary:
            if isinstance(primary, str):
                primary = primary.split()
            sqlcolumns += [u"PRIMARY KEY (%s)" % _ATOMSEQ(primary)]
        for index in indexes:
            if isinstance(index, str):
                index = index.split()
            sqlcolumns += [u"INDEX %s (%s)" % (_ATOM("-".join(index)), _ATOMSEQ(index))]
        if constraints:
            for constraint in constraints:
                sqlcolumns += [u"CONSTRAINT %s %s (%s)" % (constraint[0], _ATOM(constraint[1]), _ATOMSEQ(constraint[2]))]
        if drop:
            sql = (u"DROP TABLE IF EXISTS %s;\n" % _ATOM(table) +
                   u"CREATE TABLE %s (\n " % _ATOM(table))
        else:
            sql = u"CREATE TABLE IF NOT EXISTS %s (\n " % _ATOM(table)

        sql += u",\n ".join(sqlcolumns) + u") "

        for key, value in list(kwargs.items()):
            sql += u" %s = %s " % (key, value)
        sql += u";"
        self.execute(sql)

    def disable_keys(self, *tables):
        for table in tables:
            self.execute("ALTER TABLE %s DISABLE KEYS;" % _ATOM(table))

    def enable_keys(self, *tables):
        for table in tables:
            self.execute("ALTER TABLE %s ENABLE KEYS;" % _ATOM(table))

    def disable_checks(self):
        self.execute("SET FOREIGN_KEY_CHECKS = 0;")
        self.execute("SET UNIQUE_CHECKS = 0;")
        self.execute("SET AUTOCOMMIT = 0;")

    def enable_checks(self):
        self.execute("SET UNIQUE_CHECKS = 1;")
        self.execute("SET FOREIGN_KEY_CHECKS = 1;")
        self.execute("COMMIT;")

    def lock(self, *tables):
        t = ", ".join([_ATOM(table) + " WRITE" for table in tables])
        self.execute(u"LOCK TABLES %s;" % t)

    def unlock(self):
        self.execute(u"UNLOCK TABLES;")

    def set_names(self, encoding="utf8"):
        self.execute(u"SET NAMES %s;" % encoding)

    def delete_rows(self, table, conditions):
        conditions = " AND ".join(["%s = %s" % (_ATOM(k), _VALUE(v)) for (k, v) in list(conditions.items())])
        self.execute(u"DELETE FROM %s WHERE %s;" % (_ATOM(table), conditions))

    def drop_table(self, *tables):
        self.execute(u"DROP TABLE IF EXISTS %s;" % _ATOMSEQ(tables))

    def rename_table(self, tables):
        renames = [u"%s TO %s" % (_ATOM(old), _ATOM(new)) for old, new in list(tables.items())]
        self.execute(u"RENAME TABLE %s;" % ", ".join(renames))

    def add_row(self, table, rows, extra=""):
        if isinstance(rows, dict):
            rows = [rows]
        table = _ATOM(table)
        sql = []
        values = []
        input_length = 0

        def insert(values, extra=""):
            if extra:
                extra = "\n" + extra
            return u"INSERT INTO %s (%s) VALUES\n" % (table, ", ".join(sorted(rows[0].keys()))) + ",\n".join(values) + "%s;" % extra

        for row in rows:
            if isinstance(row, dict):
                rowlist = sorted(list(row.items()), key=lambda x: x[0])
                valueline = u"(%s)" % (_VALUESEQ([x[1] for x in rowlist]))
                input_length += len(valueline)
                if input_length > MAX_ALLOWED_PACKET:
                    sql.append(insert(values, extra))
                    values = []
                    input_length = len(valueline)
                values += [valueline]

        if values:
            sql.append(insert(values, extra))
        self.execute("\n".join(sql))


def _TYPE(typ):
    return _TYPE_CONVERSIONS.get(typ, typ)

_TYPE_CONVERSIONS = {str: "varchar(255)",
                     str: "varchar(255)",
                     int: "int(11)",
                     float: "float",
                     'year': "year(4)",
                     }


def _ATOM(atom):
    assert isinstance(atom, str)
    return "`%s`" % (atom,)


def _ATOMSEQ(atoms):
    assert isinstance(atoms, (list, tuple))
    return ", ".join(map(_ATOM, atoms))


def _VALUE(val):
    assert (val is None) or isinstance(val, (str, int, float))
    if val is None:
        return "NULL"
    if isinstance(val, str):
        return "'%s'" % (_ESCAPE(val),)
    else:
        return "%s" % (val,)


def _VALUESEQ(vals):
    assert isinstance(vals, (list, tuple))
    return ", ".join(map(_VALUE, vals))


def _DICT(dct, filter_null=False):
    assert isinstance(dct, dict)
    return ", ".join("%s = %s" % (_ATOM(k), _VALUE(v)) for (k, v) in list(dct.items())
                     if not (filter_null and v is None))


def _ESCAPE(string):
    return string.replace("\\", "\\\\").replace("'", r"\'")
