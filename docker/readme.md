## Build

```
docker compose -f docker/compose.yml build
```

Rebuild after changing `docker.requirements.txt` (forces dependency reinstall):

```
docker compose -p "$USER" -f docker/compose.yml build --no-cache from_me
```

## Run

```
docker compose -f docker/compose.yml run from_others
```

```
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -p "$USER" -f docker/compose.yml run --rm from_me
```

# Move videos

python --fill_author.py --author=junsoo
python move_author_files.py --author=junsoo --config=config/config.yaml

## Exit without closing

```
Ctrl + P, then Ctrl + Q
```
