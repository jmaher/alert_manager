.PHONY: make_data clean_data populate_data

UNAME_S := $(shell uname -s)

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "  init_data to make the data containers"
	@echo "  clean_data to remove the data containers"
	@echo "  rebuild_data to remove, and then build the data containers"
	@echo "  init_containers to build the application containers"
	@echo "  clean_containers to remove old containers and images"
	@echo "  init_config to build the fig configuration"
	@echo "  clean to remove all docker data, containers, and images"
	@echo "  all to build everything from scratch"

APP_CONTAINERS :=web db
DATA_CONTAINERS :=data

init_data:
	$(foreach container, $(DATA_CONTAINERS), docker build --no-cache --rm -t ateam/alert_manager_$(container) alert_manager_$(container);)
	$(foreach container, $(DATA_CONTAINERS), docker run --name alert_manager_$(container) ateam/alert_manager_$(container);)

clean_data:
	# remove named data containers
	-$(foreach container, $(DATA_CONTAINERS), docker rm --force alert_manager_$(container);)
	# then remove data images after container dependencies are gone
	-$(foreach container, $(DATA_CONTAINERS), docker rmi ateam/alert_manager_$(container);)

rebuild_data: clean_data init_data

init_containers:
	docker build --rm -t ateam/alert_manager_db alert_manager_db
	docker run --rm --volumes-from alert_manager_data ateam/alert_manager_db /usr/local/bin/provision_mysql.sh
	@cp ../requirements.txt alert_manager_web/requirements.txt
	docker build --rm -t ateam/alert_manager_web alert_manager_web
	@rm alert_manager_web/requirements.txt

clean_containers:
	-docker ps -a |grep alert_manager |awk '{print $$1}' |xargs docker rm

clean_images:
	-docker images -a |grep alert_manager |awk '{print $$3}' |xargs docker rmi

make init_config:
	@bash build_configs.sh

make clean: clean_data clean_containers clean_images

make all: init_data init_containers init_config
