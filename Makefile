build:
	docker build -f docker/Dockerfile -t apprepo .
	docker run -v "$(PWD):/src" -w "/src"  apprepo projector devenv build --use-isolated-python --force-bootstrap

run:
	docker run -it -v "$(PWD):/src" -w "/src" apprepo $(CMD)

testserver:
	docker-compose -f docker/docker-compose.yml -p apprepo up -d

stop_testserver:
	docker-compose -f docker/docker-compose.yml -p apprepo stop

restart_testserver: stop_testserver testserver


process_file:
	mkdir -p data/artifacts/incoming/main-stable
	cp $(FILE) data/artifacts/incoming/main-stable
	$(eval now := $(shell date +"%Y-%m-%dT%H:%M:%S"))
	docker exec -it apprepo_webserver_1 /src/bin/eapp_repo service process-incoming main-stable
	docker logs apprepo_rpcserver_1 --since "$(now)"

release:
	docker run -it -v "$(HOME)/.ssh:/root/.ssh" -v "$(PWD):/src" -w "/src" apprepo projector version release $(VERSION)
