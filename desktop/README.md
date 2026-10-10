# Desktop version

`launcher.py` detects an already healthy ThreatDefender service before starting
another one. Otherwise, it starts the same local engine used by the web dashboard
and Chrome extension, waits for `/api/health`, and opens the dashboard on
`127.0.0.1`. If the service cannot start or become healthy, the launcher reports
the configured port and exits without leaving its startup thread running.

On Windows, double-click `start.bat` in the project root.
