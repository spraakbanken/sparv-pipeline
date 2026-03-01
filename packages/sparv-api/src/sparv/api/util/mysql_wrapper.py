"""Util class for creating MySQL files."""

from __future__ import annotations

import operator
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sparv.api import get_logger

from . import system

logger = get_logger(__name__)

# Max size of SQL statement
MAX_ALLOWED_PACKET = 900000


class MySQL:
    """Class for executing MySQL commands or creating SQL files."""

    binaries = ("mysql", "mariadb")

    def __enter__(self) -> MySQL:
        """Enter the context and return the MySQL instance.

        Returns:
            The MySQL instance itself.
        """
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: object
    ) -> None:
        """Exit the context."""

    def __init__(
        self,
        database: str | None = None,
        host: str | None = None,
        username: str | None = None,
        password: str | None = None,
        encoding: str = "UTF-8",
        output: str | Path | None = None,
        append: bool = False,
    ) -> None:
        """Initialize the MySQL class.

        Either 'database' or 'output' must be used. When 'output' is used, the SQL statements will be written to a file
        instead of being executed.

        Args:
            database: The name of the database.
            host: The host of the database.
            username: The username for the database.
            password: The password for the database.
            encoding: The encoding to use.
            output: The output file path.
            append: Whether to append to the output file.
        """
        assert database or output, "Either 'database' or 'output' must be used."
        if database:
            self.arguments = [database]
            if username:
                self.arguments += ["-u", username]
            if password:
                self.arguments += ["-p", password]
        self.host = host
        self.encoding = encoding
        self.output = Path(output) if output else None
        self.first_output = True
        if self.output and not append and self.output.exists():
            self.output.unlink()

    def execute(self, sql: str, *args: Any) -> None:
        """Execute a SQL statement or add it to the output file.

        Args:
            sql: The SQL statement.
            args: Arguments to be inserted into the SQL statement using %.
        """
        if self.first_output:
            if sql.strip():
                sql = "SET @@session.long_query_time = 1000;\n" + sql
            self.first_output = False
        if self.output:
            # Write SQL statement to file
            with self.output.open("a", encoding=self.encoding) as outfile:
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
                    encoding=self.encoding,
                )
            if out:
                logger.info("MySQL: %s", out)
            if err:
                logger.error("MySQL: %s", err)
        # return out

    def create_table(
        self,
        table: str,
        drop: bool,
        columns: list[tuple[str, Any, Any, Any]],
        primary: str | list[str] | None = None,
        indexes: list[str | list[str]] | None = None,
        constraints: list[tuple[str, str, list[str]]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Create a table in the database.

        Args:
            table: The name of the table.
            drop: Whether to drop the table if it exists.
            columns: A list of columns with their types, extra options and default values.
            primary: The primary key column(s).
            indexes: A list of indexes.
            constraints: A list of constraints.
            **kwargs: Additional options for the table creation.
        """
        sqlcolumns = [
            f"  {_atom(name)} {_type(typ)} {extra or ''} DEFAULT {_value(default)}"
            for name, typ, default, extra in columns
        ]
        if primary:
            if isinstance(primary, str):
                primary = primary.split()
            sqlcolumns += [f"PRIMARY KEY ({_atomseq(primary)})"]
        if indexes:
            for index in indexes:
                if isinstance(index, str):
                    index = index.split()  # noqa: PLW2901
                sqlcolumns += [f"INDEX {_atom('-'.join(index))} ({_atomseq(index)})"]
        if constraints:
            for constraint in constraints:
                sqlcolumns += [f"CONSTRAINT {constraint[0]} {_atom(constraint[1])} ({_atomseq(constraint[2])})"]
        if drop:
            sql = f"DROP TABLE IF EXISTS {_atom(table)};\nCREATE TABLE {_atom(table)} (\n "
        else:
            sql = f"CREATE TABLE IF NOT EXISTS {_atom(table)} (\n "

        sql += ",\n ".join(sqlcolumns) + ") "

        for key, value in kwargs.items():
            sql += f" {key} = {value} "
        sql += ";"
        self.execute(sql)

    def disable_keys(self, *tables: Iterable[str]) -> None:
        """Disable keys for the specified tables.

        Args:
            tables: The names of the tables.
        """
        for table in tables:
            self.execute(f"ALTER TABLE {_atom(table)} DISABLE KEYS;")

    def enable_keys(self, *tables: Iterable[str]) -> None:
        """Enable keys for the specified tables.

        Args:
            tables: The names of the tables.
        """
        for table in tables:
            self.execute(f"ALTER TABLE {_atom(table)} ENABLE KEYS;")

    def disable_checks(self) -> None:
        """Disable checks."""
        self.execute("SET FOREIGN_KEY_CHECKS = 0;")
        self.execute("SET UNIQUE_CHECKS = 0;")
        self.execute("SET AUTOCOMMIT = 0;")

    def enable_checks(self) -> None:
        """Enable checks."""
        self.execute("SET UNIQUE_CHECKS = 1;")
        self.execute("SET FOREIGN_KEY_CHECKS = 1;")
        self.execute("COMMIT;")

    def lock(self, *tables: Iterable[str]) -> None:
        """Lock tables.

        Args:
            tables: The names of the tables.
        """
        t = ", ".join([_atom(table) + " WRITE" for table in tables])
        self.execute(f"LOCK TABLES {t};")

    def unlock(self) -> None:
        """Unlock all tables."""
        self.execute("UNLOCK TABLES;")

    def set_names(self, encoding: str = "utf8mb4") -> None:
        """Set the encoding for the connection.

        Args:
            encoding: The encoding to use.
        """
        self.execute(f"SET NAMES {encoding};")

    def delete_rows(self, table: str, conditions: dict[str, Any]) -> None:
        """Delete rows from a table based on conditions.

        Args:
            table: The name of the table.
            conditions: A dictionary of conditions to match rows for deletion.
        """
        conditions = " AND ".join([f"{_atom(k)} = {_value(v)}" for (k, v) in conditions.items()])
        self.execute(f"DELETE FROM {_atom(table)} WHERE {conditions};")

    def drop_table(self, *tables: str) -> None:
        """Drop the specified tables if they exist.

        Args:
            tables: The names of the tables to drop.
        """
        self.execute(f"DROP TABLE IF EXISTS {_atomseq(tables)};")

    def drop_view(self, *views: str) -> None:
        """Drop the specified views if they exist.

        Args:
            views: The names of the views to drop.
        """
        self.execute(f"DROP VIEW IF EXISTS {_atomseq(views)};")

    def rename_table(self, tables: dict[str, str]) -> None:
        """Rename tables in the database.

        Args:
            tables: A dictionary where keys are old table names and values are new table names.
        """
        renames = [f"{_atom(old)} TO {_atom(new)}" for old, new in tables.items()]
        self.execute(f"RENAME TABLE {', '.join(renames)};")

    def add_row(self, table: str, rows: list[dict[str, Any]] | dict[str, Any], extra: str = "") -> None:
        """Add a row or rows to a table.

        Args:
            table: The name of the table.
            rows: A dictionary or list of dictionaries representing the row(s) to add.
            extra: Additional SQL to append to the insert statement.
        """
        if isinstance(rows, dict):
            rows = [rows]
        table = _atom(table)
        sql = []
        values = []
        input_length = 0

        def insert(_values: list[str], _extra: str = "") -> str:
            if _extra:
                _extra = "\n" + _extra
            return (
                f"INSERT INTO {table} ({', '.join(sorted(rows[0].keys()))}) VALUES\n"
                + ",\n".join(_values)
                + f"{_extra};"
            )

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


def _type(typ: type | str) -> str:
    """Convert a Python type to a MySQL type.

    Args:
        typ: The Python type.

    Returns:
        The corresponding MySQL type.
    """
    return _TYPE_CONVERSIONS.get(typ, typ)


_TYPE_CONVERSIONS = {
    str: "varchar(255)",
    int: "int(11)",
    float: "float",
    "year": "year(4)",
}


def _atom(atom: str) -> str:
    """Enclose identifiers in backticks.

    Args:
        atom: The string to enclose.

    Returns:
        The enclosed string.
    """
    assert isinstance(atom, str)
    return f"`{atom}`"


def _atomseq(atoms: Iterable[str]) -> str:
    """Enclose a sequence of identifiers in backticks.

    Args:
        atoms: The sequence of strings to enclose.

    Returns:
        The enclosed sequence.
    """
    assert isinstance(atoms, (list, tuple))
    return ", ".join(map(_atom, atoms))


def _value(val: str | int | float | None) -> str:
    """Convert a value to format suitable for SQL.

    Args:
        val: The value to convert.

    Returns:
        The converted value.
    """
    assert (val is None) or isinstance(val, (str, int, float))
    if val is None:
        return "NULL"
    if isinstance(val, str):
        return f"'{_escape(val)}'"
    return f"{val}"


def _valueseq(vals: Iterable[str | int | float]) -> str:
    """Convert a sequence of values to format suitable for SQL.

    Args:
        vals: The sequence of values to convert.

    Returns:
        The converted sequence.
    """
    assert isinstance(vals, (list, tuple))
    return ", ".join(map(_value, vals))


def _dict(dct: dict, filter_null: bool = False) -> str:
    """Convert a dictionary to a comma-separated list of key-value pairs.

    Args:
        dct: The dictionary to convert.
        filter_null: Whether to filter out None values.

    Returns:
        The converted dictionary.
    """
    assert isinstance(dct, dict)
    return ", ".join(f"{_atom(k)} = {_value(v)}" for (k, v) in dct.items() if not (filter_null and v is None))


def _escape(string: str) -> str:
    """Escape a string for use in SQL.

    Args:
        string: The string to escape.

    Returns:
        The escaped string.
    """
    return string.replace("\\", "\\\\").replace("'", r"\'")
