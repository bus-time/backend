#!/bin/sh


# Stop on unintialized variable usage
set -u

# Stop on first error
set -e


function print_help() {
    echo "Usage: push-to-heroku [-f | --force]"
    echo "Options:"
    echo "    -f, --force"
    echo "        Use 'git push --force' instead of just 'git push'."
}

function print_unknown_args() {
    echo "Unknown arguments specified."
    print_help
}

function stop_heroku() {
    heroku maintenance:on
    heroku ps:scale web=0
}

function deploy_application() {
    git push heroku HEAD:master $PUSH_FORCE

    heroku run "alembic -c config/alembic.ini upgrade head"
}

function start_heroku() {
    heroku ps:scale web=1
    heroku maintenance:off
}


# Run

PUSH_FORCE=""
while [ $# -gt 0 ];
do
    case "$1" in
        -f|--force) PUSH_FORCE="--force";;
        -h|--help)  print_help;
                    exit;;
        *)          print_unknown_args;
                    exit;;
    esac
    shift
done


stop_heroku
deploy_application
start_heroku
