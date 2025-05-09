# High level code


#### Supervisor Configuration

Create a configuration file for the script in `/etc/supervisor/supervisord.conf`

```ini
sudo nano /etc/supervisor/supervisord.conf

add program

[program:telegram_cost_tracker]
command=/home/gws/project/telegram_cost_tracker/run_cost_tracker.sh
directory=directory=/home/gws/project/telegram_cost_tracker
autostart=true
autorestart=true
stderr_logfile=/home/gws/project/telegram_cost_tracker/log/run_cost_tracker.err.log
stdout_logfile=/home/gws/project/telegram_cost_tracker/log/run_cost_tracker.out.log
stopasgroup=true
killasgroup=true
```

#### Update Supervisor

Once the configuration is added, update `supervisord` to read the new configuration:

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

#### Start the Program

To start the program, use:

```bash
sudo supervisorctl start telegram_cost_tracker
```
