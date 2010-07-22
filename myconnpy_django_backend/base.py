"""
MySQL database backend for Django using MySQL Connector/Python.

"""

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseOperations, util
try:
    import mysql.connector as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading MySQLdb module: %s" % e)

# We want version (1, 2, 1, 'final', 2) or later. We can't just use
# lexicographic ordering in this check because then (1, 2, 1, 'gamma')
# inadvertently passes the version test.
version = Database.__version__
if ( version[:3] < (0, 0, 2) ):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("MySQL Connector/Python 0.0.2 or newer is required; you have %s" % Database.__version__)

import mysql.connector.conversion
import re

from django.db.backends import *
from django.db.backends.mysql import base as mysqldb_base
from django.db.backends.mysql.client import DatabaseClient
from django.db.backends.mysql.creation import DatabaseCreation
from django.db.backends.mysql.introspection import DatabaseIntrospection
from django.db.backends.mysql.validation import DatabaseValidation
from django.utils.safestring import SafeString, SafeUnicode

# Raise exceptions for database warnings if DEBUG is on
from django.conf import settings

# NOTE: Disabling this since `mysql.connector.Database.Warning` is a
# subclass of StandardError instead of a "warning"
if False: #settings.DEBUG:
    from warnings import filterwarnings
    filterwarnings("error", category=Database.Warning)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError


class DjangoMySQLConverter(Database.conversion.MySQLConverter):
    pass
    """
    def _TIME_to_python(self, v, dsc=None):
        return util.typecast_time(v)

    def _decimal(self, v, desc=None):
        return util.typecast_decimal(v)
    """
# This should match the numerical portion of the version numbers (we can treat
# versions like 5.0.24 and 5.0.24a as the same). Based on the list of version
# at http://dev.mysql.com/doc/refman/4.1/en/news.html and
# http://dev.mysql.com/doc/refman/5.0/en/news.html .
server_version_re = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{1,2})')

# MySQLdb-1.2.1 and newer automatically makes use of SHOW WARNINGS on
# MySQL-4.1 and newer, so the MysqlDebugWrapper is unnecessary. Since the
# point is to raise Warnings as exceptions, this can be done with the Python
# warning module, and this is setup when the connection is created, and the
# standard util.CursorDebugWrapper can be used. Also, using sql_mode
# TRADITIONAL will automatically cause most warnings to be treated as errors.

class DatabaseFeatures(BaseDatabaseFeatures):
    allows_group_by_pk = True
    autoindexes_primary_keys = False
    inline_fk_references = False
    related_fields_match_type = True
    update_can_self_select = False


class DatabaseWrapper(BaseDatabaseWrapper):

    operators = {
        'exact': '= %s',
        'iexact': 'LIKE %s',
        'contains': 'LIKE BINARY %s',
        'icontains': 'LIKE %s',
        'regex': 'REGEXP BINARY %s',
        'iregex': 'REGEXP %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE BINARY %s',
        'endswith': 'LIKE BINARY %s',
        'istartswith': 'LIKE %s',
        'iendswith': 'LIKE %s',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.server_version = None

        self.features = DatabaseFeatures()
        self.ops = mysqldb_base.DatabaseOperations()
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = DatabaseValidation(self)

    def _valid_connection(self):
        if self.connection is not None:
            try:
                self.connection.ping()
                return True
            except DatabaseError:
                self.connection.close()
                self.connection = None
        return False

    def _cursor(self):
        if not self._valid_connection():
            kwargs = {
                #'conv': django_conversions,
                'charset': 'utf8',
                'use_unicode': True,
            }
            settings_dict = self.settings_dict
            if settings_dict['USER']:
                kwargs['user'] = settings_dict['USER']
            if settings_dict['NAME']:
                kwargs['db'] = settings_dict['NAME']
            if settings_dict['PASSWORD']:
                kwargs['passwd'] = settings_dict['PASSWORD']
            if settings_dict['HOST'].startswith('/'):
                kwargs['unix_socket'] = settings_dict['HOST']
            elif settings_dict['HOST']:
                kwargs['host'] = settings_dict['HOST']
            if settings_dict['PORT']:
                kwargs['port'] = int(settings_dict['PORT'])
            self.connection = Database.connect(**kwargs)
            self.connection.set_converter_class(DjangoMySQLConverter)
        cursor = self.connection.cursor()
        return cursor

    def _rollback(self):
        try:
            BaseDatabaseWrapper._rollback(self)
        except Database.NotSupportedError:
            pass

    def get_server_version(self):
        if not self.server_version:
            if not self._valid_connection():
                self.cursor()
            self.server_version = self.connection.get_server_version()
            #m = server_version_re.match(self.connection.get_server_version())
            #if not m:
            #    raise Exception('Unable to determine MySQL version from version string %r' % self.connection.get_server_version())
            #self.server_version = tuple([int(x) for x in m.groups()])
        return self.server_version
