
#!/bin/bash
# APP_HOME is inherited from the environment (set in the Dockerfile, validated by docker-entrypoint.sh).
# The guard below also allows this script to be run standalone inside the container.
if [ -z "${APP_HOME:-}" ]; then
    printf >&2 'error: APP_HOME is not set.\n'
    exit 1
fi
if [ ! -d "$APP_HOME" ]; then
    printf >&2 'error: APP_HOME="%s" does not point to an existing directory.\n' "$APP_HOME"
    exit 1
fi

iop --init

iris session iris < "$APP_HOME/iris.script"

iop -m "$APP_HOME/src/EAI/python/settings.py"