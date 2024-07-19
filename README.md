# Info

## Containers commands

```sh
# run containers
docker-compose up

# list containers
docker ps --all
docker ps --filter status=paused

# connect to container
docker exec -it fastapi-app-1 sh

# end container 
docker kill fastapi-app-1

# delete container
docker rm fastapi-app-1

# delete image
docker image rm fastapi-app

```

## install libraries

```sh
pip install --no-cache-dir -r requirements.txt
```

## tests

```sh
pytest
```
