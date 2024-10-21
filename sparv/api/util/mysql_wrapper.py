"""Util function for creating mysql files."""

import operator
import os

from sparv.api import get_logger

from . import system

logger = get_logger(__name__)

# Max size of SQL statement
MAX_ALLOWED_PACKET = 900000


class MySQL:
    binaries = ("mysql", "mariadb")

    def __init__(
        self, database=None, host=None, username=None, password=None, encoding="UTF-8", output=None, append=False
    ):
        assert database or output, "Either 'database' or 'output' must be used."
        if database:
            self.arguments = [database]
            if username:
                self.arguments += ["-u", username]
            if password:
                self.arguments += ["-p", password]
        self.host = host
        self.encoding = encoding
        self.output = output
        self.first_output = True
        if self.output and not append and os.path.exists(self.output):
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
            if self.host is None:
                out, err = system.call_binary(self.binaries, self.arguments, sql % args, encoding=self.encoding)
            else:
                out, err = system.call_binary(
                    "ssh",
                    [self.host, " ".join([self.binaries[0], *self.arguments])],
                    stdin=sql % args,
                    encoding=self.encoding
                )
            if out:
                logger.info("MySQL: %s", out)
            if err:
                logger.error("MySQL: %s", err)
        # return out

    def create_table(self, table, drop, columns, primary=None, indexes=None, constraints=None, **kwargs):
        sqlcolumns = [f"  {_atom(name)} {_type(typ)} {extra or ''} DEFAULT {_value(default)}"
                      for name, typ, default, extra in columns]
        if primary:
            if isinstance(primary, str):
                primary = primary.split()
            sqlcolumns += [f"PRIMARY KEY ({_atomseq(primary)})"]
        if indexes:
            for index in indexes:
                if isinstance(index, str):
                    index = index.split()
                sqlcolumns += [f"INDEX {_atom('-'.join(index))} ({_atomseq(index)})"]
        if constraints:
            for constraint in constraints:
                sqlcolumns += [f"CONSTRAINT {constraint[0]} {_atom(constraint[1])} ({_atomseq(constraint[2])})"]
        if drop:
            sql = (f"DROP TABLE IF EXISTS {_atom(table)};\n"
                   f"CREATE TABLE {_atom(table)} (\n ")
        else:
            sql = f"CREATE TABLE IF NOT EXISTS {_atom(table)} (\n "

        sql += ",\n ".join(sqlcolumns) + ") "

        for key, value in kwargs.items():
            sql += f" {key} = {value} "
        sql += ";"
        self.execute(sql)

    def disable_keys(self, *tables):
        for table in tables:
            self.execute(f"ALTER TABLE {_atom(table)} DISABLE KEYS;")

    def enable_keys(self, *tables):
        for table in tables:
            self.execute(f"ALTER TABLE {_atom(table)} ENABLE KEYS;")

    def disable_checks(self):
        self.execute("SET FOREIGN_KEY_CHECKS = 0;")
        self.execute("SET UNIQUE_CHECKS = 0;")
        self.execute("SET AUTOCOMMIT = 0;")

    def enable_checks(self):
        self.execute("SET UNIQUE_CHECKS = 1;")
        self.execute("SET FOREIGN_KEY_CHECKS = 1;")
        self.execute("COMMIT;")

    def lock(self, *tables):
        t = ", ".join([_atom(table) + " WRITE" for table in tables])
        self.execute(f"LOCK TABLES {t};")

    def unlock(self):
        self.execute("UNLOCK TABLES;")

    def set_names(self, encoding="utf8mb4"):
        self.execute(f"SET NAMES {encoding};")

    def delete_rows(self, table, conditions):
        conditions = " AND ".join([f"{_atom(k)} = {_value(v)}" for (k, v) in conditions.items()])
        self.execute(f"DELETE FROM {_atom(table)} WHERE {conditions};")

    def drop_table(self, *tables):
        self.execute(f"DROP TABLE IF EXISTS {_atomseq(tables)};")

    def rename_table(self, tables):
        renames = [f"{_atom(old)} TO {_atom(new)}" for old, new in tables.items()]
        self.execute(f"RENAME TABLE {', '.join(renames)};")

    def add_row(self, table, rows, extra=""):
        if isinstance(rows, dict):
            rows = [rows]
        table = _atom(table)
        sql = []
        values = []
        input_length = 0

        def insert(_values, _extra=""):
            if _extra:
                _extra = "\n" + _extra
            return f"INSERT INTO {table} ({', '.join(sorted(rows[0].keys()))}) VALUES\n" + ",\n".join(
                _values) + f"{_extra};"

        for row in rows:
            if isinstance(row, dict):
                rowlist = sorted(row.items(), key=operator.itemgetter(0))
                valueline = f"({_valueseq([x[1] for x in rowlist])})"
                input_length += len(valueline)
                if input_length > MAX_ALLOWED_PACKET:
                    sql.append(insert(values, extra))
                    values = []
                    input_length = len(valueline)
                values += [valueline]

        if values:
            sql.append(insert(values, extra))
        self.execute("\n".join(sql))


def _type(typ):
    return _TYPE_CONVERSIONS.get(typ, typ)


_TYPE_CONVERSIONS = {
    str: "varchar(255)",
    int: "int(11)",
    float: "float",
    "year": "year(4)",
}


def _atom(atom):
    assert isinstance(atom, str)
    return f"`{atom}`"


def _atomseq(atoms):
    assert isinstance(atoms, (list, tuple))
    return ", ".join(map(_atom, atoms))


def _value(val):
    assert (val is None) or isinstance(val, (str, int, float))
    if val is None:
        return "NULL"
    if isinstance(val, str):
        return f"'{_escape(val)}'"
    else:
        return f"{val}"


def _valueseq(vals):
    assert isinstance(vals, (list, tuple))
    return ", ".join(map(_value, vals))


def _dict(dct, filter_null=False):
    assert isinstance(dct, dict)
    return ", ".join(f"{_atom(k)} = {_value(v)}" for (k, v) in dct.items()
                     if not (filter_null and v is None))


def _escape(string):
    return string.replace("\\", "\\\\").replace("'", r"\'")
