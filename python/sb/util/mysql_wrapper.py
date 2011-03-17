# -*- coding: utf-8 -*-

import system
import log
import constants

class MySQL(object):
    binaries = ('mysql', 'mysql5')
    
    def __init__(self, database, username=None, password=None, encoding="ascii", output=""):
        self.arguments = [database]
        if username:
            self.arguments += ['-u', username]
        if password:
            self.arguments += ['-p', password]
        self.encoding = encoding
        self.output = output

    def execute(self, sql, *args):
        if self.output:
            # Write SQL statement to file
            with open(self.output, "a") as outfile:
                print >>outfile, sql.encode(constants.UTF8)
        else:
            # Execute SQL statement
            out, err = system.call_binary(self.binaries[0], self.arguments, sql % args,
                                      binary_names=self.binaries, encoding=self.encoding)
            if out:
                log.info("MySQL: %s", out)
            if err:
                log.error("MySQL: %s", err)
        #return out

    def create_table(self, table, drop, columns, primary=None, indexes=None, **kwargs):
        sqlcolumns = [u"  %s %s %s DEFAULT %s" %
                      (_ATOM(name), _TYPE(typ), extra or "", _VALUE(default))
                      for name, typ, default, extra in columns]
        if primary:
            if isinstance(primary, basestring):
                primary = primary.split()
            sqlcolumns += [u"PRIMARY KEY (%s)" % _ATOMSEQ(primary)]
        for index in indexes:
            if isinstance(index, basestring):
                index = index.split()
            sqlcolumns += [u"INDEX %s (%s)" % (_ATOM(index[0]), _ATOMSEQ(index))]
        
        if drop:
            sql = (u"DROP TABLE IF EXISTS %s;\n" % _ATOM(table) +
                   u"CREATE TABLE %s (\n " % _ATOM(table))
        else:
            sql = u"CREATE TABLE IF NOT EXISTS %s (\n " % _ATOM(table)
        
        sql += u",\n ".join(sqlcolumns) + u") "
        
        for key, value in kwargs.items():
            sql += u" %s = %s " % (key, _ATOM(value))
        sql += u";"
        self.execute(sql)

    def lock(self, *tables):
        t = ", ".join([_ATOM(table) + " WRITE" for table in tables])
        self.execute(u"LOCK TABLES %s;" % t)

    def unlock(self):
        self.execute(u"UNLOCK TABLES;")
    
    def delete_rows(self, table, conditions):
        conditions = " AND ".join( ["%s = %s" % (_ATOM(k), _VALUE(v)) for (k, v) in conditions.items()] )
        self.execute(u"DELETE FROM %s WHERE %s;" % (_ATOM(table), conditions))
    
    def add_row(self, table, *rows):
        assert all(isinstance(row, (dict, list, tuple)) for row in rows)
        table = _ATOM(table)
        sql = [] #[u"LOCK TABLE %s WRITE;" % table]
        for row in rows:
            if isinstance(row, dict):
                sql += [u"INSERT INTO %s SET %s;" % (table, _DICT(row, filter_null=True))]
            else:
                sql += [u"INSERT INTO %s VALUE (%s);" % (table, _VALUESEQ(row))]
        #sql += [u"UNLOCK TABLE;"]
        self.execute("\n".join(sql))


def _TYPE(typ):
    return _TYPE_CONVERSIONS.get(typ, typ)

_TYPE_CONVERSIONS = {str: "varchar(255)",
                     unicode: "varchar(255)",
                     int: "int(11)",
                     'year': "year(4)",
                     }

def _ATOM(atom):
    assert isinstance(atom, basestring)
    return "`%s`" % (atom,)

def _ATOMSEQ(atoms):
    assert isinstance(atoms, (list, tuple))
    return ", ".join(map(_ATOM, atoms))

def _VALUE(val):
    assert (val is None) or isinstance(val, (basestring, int, float))
    if val is None:
        return "NULL"
    if isinstance(val, basestring):
        return "'%s'" % (_ESCAPE(val),)
    else:
        return "%s" % (val,)

def _VALUESEQ(vals):
    assert isinstance(vals, (list, tuple))
    return ", ".join(map(_VALUE, vals))

def _DICT(dct, filter_null=False):
    assert isinstance(dct, dict)
    return ", ".join("%s = %s" % (_ATOM(k), _VALUE(v)) for (k,v) in dct.items()
                     if not (filter_null and v is None))

def _ESCAPE(string):
    return string.replace("'", r"\'")
