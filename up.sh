#!/bin/bash

docker-compose build && \
docker-compose run checker python check_blocked.py -f dmns.list && \
docker-compose run checker python check_blocked.py -f url.list && \
docker-compose run checker python check_blocked.py -f ip.list
