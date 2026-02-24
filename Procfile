web: python copy_data.py && gunicorn app:app --worker-class gthread --threads 4 --timeout 120 -b 0.0.0.0:$PORT
