from django.conf import settings
import os

def runshell():
    args = ['']
    db = settings_dict['OPTIONS'].get('db', settings_dict['NAME'])
    user = settings_dict['OPTIONS'].get('user', settings_dict['USER'])
    passwd = settings_dict['OPTIONS'].get('passwd', settings_dict['PASSWORD'])
    host = settings_dict['OPTIONS'].get('host', settings_dict['HOST'])
    port = settings_dict['OPTIONS'].get('port', settings_dict['PORT'])
    defaults_file = settings_dict['OPTIONS'].get('read_default_file')
    # Seems to be no good way to set sql_mode with CLI
    
    if defaults_file:
        args += ["--defaults-file=%s" % defaults_file]
    if user:
        args += ["--user=%s" % user]
    if passwd:
        args += ["--password=%s" % passwd]
    if host:
        args += ["--host=%s" % host]
    if port:
        args += ["--port=%s" % port]
    if db:
        args += [db]

    os.execvp('mysql', args)
