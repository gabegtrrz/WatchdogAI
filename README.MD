
# Procfile Explained

OPENBLAS_NUM_THREADS=1
Restricts NumPy / SciPy’s OpenBLAS library to a single thread.
→ Prevents CPU overuse in limited hosting environments.

gunicorn
Runs the Django app with Gunicorn, a production-grade WSGI server.
→ More reliable than Django’s built-in runserver.

--workers 2
Starts 2 worker processes.
→ Lets the app handle multiple requests concurrently.

--timeout 60
If a worker takes longer than 60 seconds to respond, it is killed and restarted.
→ Prevents stuck workers from blocking new requests.

--bind 0.0.0.0:$PORT
Binds Gunicorn to all interfaces (0.0.0.0) on the port assigned by the platform ($PORT).
→ Required so incoming traffic is properly routed to the app.

watchdog_ai.wsgi
Entry point to the Django app.
→ Points Gunicorn to the application object in watchdog_ai/wsgi.py.

--log-file -
Sends logs to standard output (-).
→ Lets the platform capture logs and display them in the dashboard.