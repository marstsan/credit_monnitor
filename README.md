# credit_monitor



## Getting started

- Install mongoDB in your environment first and it's better to configure a simple authentication (username/password).
- Install python virtual environment and install packages list in requirements.txt.
- Create a config.yaml and give correct settings, you can copy from config_sample.yaml.
- Create the first admin user by python script, for example:<br>
<pre>
    from lib.DBActions import DBActions
    dba = DBActions()
    dba.create_user('rickchen@m800.com', 'password', role='admin', displayname='Rick')
</pre>

## Start http server

- Execute a python command to start the service
<pre>   python3 app.py</pre>
- The easy way to let the process run in background
<pre>   nohup python3 app.py</pre>

## Add crontab to scedule the charge process

- Run the command to add a crontab job: 
<pre>   crontab -e</pre>
- Add this line:<br>
<pre>   5 0-23 * * * . &lt;path to venv&gt;/bin/activate && cd &lt;path to credit_monitor&gt; && python3 charge.py</pre>
