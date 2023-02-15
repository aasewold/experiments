ifndef CARLA_VERSION
$(error CARLA_VERSION must be set)
endif
ifndef TRANSFUSER_COMMIT
$(error TRANSFUSER_COMMIT must be set)
endif

BUILDDIR=build
SIFDIR=$(BUILDDIR)/sif
TARDIR=$(BUILDDIR)/tar

CARLA_SIF=$(SIFDIR)/carla.sif
TRANSFUSER_SIF=$(SIFDIR)/transfuser.sif


IDUN_HOST=idun-login1.hpc.ntnu.no
IDUN_WORKDIR=work/thesis/datagen
IDUN_RUNDIR=$(IDUN_WORKDIR)/run
IDUN_SIFDIR=$(IDUN_WORKDIR)/sif


.PHONY: job idun idun-carla idun-transfuser

job: idun | $(IDUN_RUNDIR)
	ssh $(IDUN_HOST) "cd $(IDUN_RUNDIR) && sbatch ../job.slurm"

idun: idun-carla idun-transfuser idun-extra

idun-carla: $(BUILDDIR)/.idun-carla | $(BUILDDIR)
$(BUILDDIR)/.idun-carla: $(CARLA_SIF) | $(IDUN_SIFDIR)
	rsync -zhP $(CARLA_SIF) $(IDUN_HOST):$(IDUN_SIFDIR)/
	touch $@

idun-transfuser: $(BUILDDIR)/.idun-transfuser | $(BUILDDIR)
$(BUILDDIR)/.idun-transfuser: $(TRANSFUSER_SIF) | $(IDUN_SIFDIR)
	rsync -zhP $(TRANSFUSER_SIF) $(IDUN_HOST):$(IDUN_SIFDIR)/
	touch $@

IDUN_EXTRA_FILES := $(shell find ./idun -type f -print)
idun-extra: $(BUILDDIR)/.idun-extra | $(BUILDDIR)
$(BUILDDIR)/.idun-extra: $(IDUN_EXTRA_FILES) | $(IDUN_WORKDIR)
	rsync -rzhP ./idun/ $(IDUN_HOST):$(IDUN_WORKDIR)/
	touch $@


.PHONY: $(IDUN_WORKDIR) $(IDUN_SIFDIR) $(IDUN_RUNDIR)
$(IDUN_WORKDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_WORKDIR)

$(IDUN_SIFDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_SIFDIR)

$(IDUN_RUNDIR):
	ssh $(IDUN_HOST) mkdir -p $(IDUN_RUNDIR)


.PHONY: sif carla transfuser

sif: carla transfuser

carla: $(SIFDIR)/carla.sif
transfuser: $(SIFDIR)/transfuser.sif


# Remove any "experiments/" prefix from the commit branch name
TRANSFUSER_VERSION := $(TRANSFUSER_COMMIT:experiments/%=%)
TRANSFUSER_TAG := aasewold/transfuser:datagen-$(TRANSFUSER_VERSION)
TRANSFUSER_DOCKERFILE := ../common/transfuser.dockerfile

$(SIFDIR)/transfuser.sif: $(TARDIR)/transfuser.docker.tar | $(SIFDIR)
	apptainer build $(SIFDIR)/transfuser.sif docker-archive:$(TARDIR)/transfuser.docker.tar 

$(TARDIR)/transfuser.docker.tar: $(TRANSFUSER_DOCKERFILE) | $(TARDIR)
	docker buildx build \
		-t $(TRANSFUSER_TAG) \
		--build-arg CARLA_VERSION=$(CARLA_VERSION) \
		--build-arg TRANSFUSER_COMMIT=$(TRANSFUSER_COMMIT) \
		- < $(TRANSFUSER_DOCKERFILE)
	docker save $(TRANSFUSER_TAG) > $(TARDIR)/transfuser.docker.tar


CARLA_TAG := aasewold/carla:datagen-$(CARLA_VERSION)
CARLA_DOCKERFILE := ../common/carla-$(CARLA_VERSION).dockerfile

$(SIFDIR)/carla.sif: $(TARDIR)/carla.docker.tar | $(SIFDIR)
	apptainer build $(SIFDIR)/carla.sif docker-archive:$(TARDIR)/carla.docker.tar

$(TARDIR)/carla.docker.tar: $(CARLA_DOCKERFILE) | $(TARDIR)
	docker buildx build \
		-t $(CARLA_TAG) \
		--build-arg CARLA_VERSION=$(CARLA_VERSION) \
		- < $(CARLA_DOCKERFILE)
	docker save $(CARLA_TAG) > $(TARDIR)/carla.docker.tar

$(CARLA_DOCKERFILE):
	$(error $(CARLA_DOCKERFILE) does not exist.)


$(BUILDDIR):
	mkdir -p $(BUILDDIR)

$(SIFDIR):
	mkdir -p $(SIFDIR)

$(TARDIR):
	mkdir -p $(TARDIR)
