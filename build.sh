#!/bin/bash

# Apply database migrations
python3 manage.py migrate --noinput

# Collect static files
python3 manage.py collectstatic --noinput
