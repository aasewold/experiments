ifndef CARLA_VERSION
$(error CARLA_VERSION must be set)
endif

ifndef TRANSFUSER_COMMIT
$(error TRANSFUSER_COMMIT must be set)
endif

TRANSFUSER_SHA := $(shell curl -s "https://api.github.com/repos/aasewold/transfuser/commits/${TRANSFUSER_COMMIT}" | jq -r .sha | head -c 8)

BUILDDIR=build
TF_BUILDDIR=$(BUILDDIR)/transfuser-$(TRANSFUSER_SHA)
CARLA_BUILDDIR=$(BUILDDIR)/carla-$(CARLA_VERSION)

CARLA_SIF=$(CARLA_BUILDDIR)/carla.sif
CARLA_TAR=$(CARLA_BUILDDIR)/carla.tar
TF_SIF=$(TF_BUILDDIR)/transfuser.sif
TF_TAR=$(TF_BUILDDIR)/transfuser.tar

TF_TAG := aasewold/transfuser:datagen-$(TRANSFUSER_SHA)
TF_DOCKERFILE := ../common/transfuser.dockerfile

CARLA_TAG := aasewold/carla:datagen-$(CARLA_VERSION)
CARLA_DOCKERFILE := ../common/carla-$(CARLA_VERSION).dockerfile


IDUN_HOST=idun-login1.hpc.ntnu.no
IDUN_WORKDIR=work/thesis/datagen
IDUN_RUNDIR=$(IDUN_WORKDIR)/run
IDUN_SIFDIR=$(IDUN_WORKDIR)/sif

.PHONY: job idun idun-carla idun-transfuser

job: idun | $(IDUN_RUNDIR)
	ssh $(IDUN_HOST) "cd $(IDUN_RUNDIR) && ../submit.sh"

idun: idun-carla idun-transfuser idun-extra

idun-carla: $(BUILDDIR)/.idun-carla | $(BUILDDIR)
$(BUILDDIR)/.idun-carla: $(CARLA_SIF) | $(IDUN_SIFDIR)
	rsync -hP $(CARLA_SIF) $(IDUN_HOST):$(IDUN_SIFDIR)/
	touch $@

idun-transfuser: $(BUILDDIR)/.idun-transfuser | $(BUILDDIR)
$(BUILDDIR)/.idun-transfuser: $(TF_SIF) | $(IDUN_SIFDIR)
	rsync -hP $(TF_SIF) $(IDUN_HOST):$(IDUN_SIFDIR)/
	touch $@

IDUN_EXTRA_FILES := $(shell find ./idun -type f -print)
idun-extra: $(BUILDDIR)/.idun-extra | $(BUILDDIR)
$(BUILDDIR)/.idun-extra: $(IDUN_EXTRA_FILES) | $(IDUN_WORKDIR)
	rsync -rhP ./idun/ $(IDUN_HOST):$(IDUN_WORKDIR)/
	touch $@


.PHONY: $(IDUN_WORKDIR) $(IDUN_SIFDIR) $(IDUN_RUNDIR)
$(IDUN_WORKDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_WORKDIR)

$(IDUN_SIFDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_SIFDIR)

$(IDUN_RUNDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_RUNDIR)


.PHONY: clean clean-carla clean-transfuser
clean: clean-carla clean-transfuser
clean-carla:
	rm -rf $(CARLA_BUILDDIR)
	docker rmi $(CARLA_TAG)

clean-transfuser:
	rm -rf $(TF_BUILDDIR)
	docker rmi $(TF_TAG)


.PHONY: sif carla transfuser

sif: carla transfuser
carla: $(CARLA_SIF)
transfuser: $(TF_SIF)


$(TF_SIF): $(TF_TAR)
	apptainer build $(TF_SIF) docker-archive:$(TF_TAR)

$(TF_TAR): $(TF_DOCKERFILE) | $(TF_BUILDDIR)
	docker buildx build \
		-t $(TF_TAG) \
		--build-arg CARLA_VERSION=$(CARLA_VERSION) \
		--build-arg TRANSFUSER_COMMIT=$(TRANSFUSER_SHA) \
		- < $(TF_DOCKERFILE)
	docker save $(TF_TAG) > $(TF_TAR)


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

$(TF_BUILDDIR):
	mkdir -p $(TF_BUILDDIR)
