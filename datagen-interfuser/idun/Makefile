ifndef CARLA_VERSION
$(error CARLA_VERSION must be set)
endif

ifndef INTERFUSER_COMMIT
$(error INTERFUSER_COMMIT must be set)
endif

INTERFUSER_SHA := $(shell curl -s "https://api.github.com/repos/aasewold/interfuser/commits/${INTERFUSER_COMMIT}" | jq -r .sha | head -c 8)

BUILDDIR=build
INTERFUSER_BUILDDIR=$(BUILDDIR)/interfuser-$(INTERFUSER_SHA)
CARLA_BUILDDIR=$(BUILDDIR)/carla-$(CARLA_VERSION)

CARLA_SIF=$(CARLA_BUILDDIR)/carla.sif
CARLA_TAR=$(CARLA_BUILDDIR)/carla.tar
INTERFUSER_SIF=$(INTERFUSER_BUILDDIR)/interfuser.sif
INTERFUSER_TAR=$(INTERFUSER_BUILDDIR)/interfuser.tar

INTERFUSER_TAG := aasewold/interfuser:datagen-$(INTERFUSER_SHA)
INTERFUSER_DOCKERFILE := ../../common/interfuser.dockerfile

CARLA_TAG := aasewold/carla:datagen-$(CARLA_VERSION)
CARLA_DOCKERFILE := ../../common/carla-$(CARLA_VERSION).dockerfile


IDUN_HOST=idun-login1.hpc.ntnu.no
IDUN_WORKDIR=work/thesis/datagen-interfuser
IDUN_SIFDIR=$(IDUN_WORKDIR)/sif

.PHONY: job idun idun-carla idun-interfuser

job: idun
	ssh $(IDUN_HOST) "cd $(IDUN_WORKDIR) && RESUME=$(RESUME) ROUTES=$(ROUTES) ./submit.sh"

idun: idun-carla idun-interfuser idun-files

idun-carla: $(BUILDDIR)/.idun-carla
$(BUILDDIR)/.idun-carla: $(CARLA_SIF) | $(IDUN_SIFDIR) $(BUILDDIR)
	rsync -hP $(CARLA_SIF) $(IDUN_HOST):$(IDUN_SIFDIR)/
	touch $@

idun-interfuser: $(BUILDDIR)/.idun-interfuser
$(BUILDDIR)/.idun-interfuser: $(INTERFUSER_SIF) | $(IDUN_SIFDIR) $(BUILDDIR)
	rsync -hP $(INTERFUSER_SIF) $(IDUN_HOST):$(IDUN_SIFDIR)/
	touch $@

IDUN_FILES := $(shell find ./files -type f -print)
idun-files: $(BUILDDIR)/.idun-files |
$(BUILDDIR)/.idun-files: $(IDUN_FILES) | $(IDUN_WORKDIR) $(BUILDDIR)
	rsync -ahP ./files/ $(IDUN_HOST):$(IDUN_WORKDIR)/
	touch $@


.PHONY: $(IDUN_WORKDIR) $(IDUN_SIFDIR)
$(IDUN_WORKDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_WORKDIR)

$(IDUN_SIFDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_SIFDIR)


.PHONY: clean clean-carla clean-interfuser
clean: clean-carla clean-interfuser
clean-carla:
	rm -rf $(CARLA_BUILDDIR)
	docker rmi $(CARLA_TAG)

clean-interfuser:
	rm -rf $(INTERFUSER_BUILDDIR)
	docker rmi $(INTERFUSER_TAG)


.PHONY: sif carla interfuser

sif: carla interfuser
carla: $(CARLA_SIF)
interfuser: $(INTERFUSER_SIF)


$(INTERFUSER_SIF): $(INTERFUSER_TAR)
	apptainer build $(INTERFUSER_SIF) docker-archive:$(INTERFUSER_TAR)

$(INTERFUSER_TAR): $(INTERFUSER_DOCKERFILE) | $(INTERFUSER_BUILDDIR)
	docker buildx build \
		-t $(INTERFUSER_TAG) \
		--build-arg CARLA_VERSION=$(CARLA_VERSION) \
		--build-arg INTERFUSER_COMMIT=$(INTERFUSER_SHA) \
		- < $(INTERFUSER_DOCKERFILE)
	docker save $(INTERFUSER_TAG) > $(INTERFUSER_TAR)


$(CARLA_SIF): $(CARLA_TAR)
	apptainer build $(CARLA_SIF) docker-archive:$(CARLA_TAR)

$(CARLA_TAR): $(CARLA_DOCKERFILE) | $(CARLA_BUILDDIR)
	docker buildx build \
		-t $(CARLA_TAG) \
		--build-arg CARLA_VERSION=$(CARLA_VERSION) \
		- < $(CARLA_DOCKERFILE)
	docker save $(CARLA_TAG) > $(CARLA_TAR)

$(CARLA_DOCKERFILE):
	$(error $(CARLA_DOCKERFILE) does not exist.)


$(BUILDDIR):
	mkdir -p $(BUILDDIR)

$(CARLA_BUILDDIR):
	mkdir -p $(CARLA_BUILDDIR)

$(INTERFUSER_BUILDDIR):
	mkdir -p $(INTERFUSER_BUILDDIR)
