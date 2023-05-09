
BUILD := build
RUN := docker compose run --user $(shell id -u):$(shell id -g) --build --rm routegen

.PHONY: csv routes scenarios copy

csv: $(BUILD)/output/routes.csv
routes: $(BUILD)/.routes
scenarios: $(BUILD)/.scenarios

copy:
	@echo "Copying routes to dest"
	cp -rf $(BUILD)/output/* ../idun/files/input/


$(BUILD)/output/routes.csv: src/gen_csv.py | $(BUILD)
	@echo "Generating CSV"
	$(RUN) python3 gen_csv.py

$(BUILD)/.routes: | $(BUILD)
	@echo "Generating routes"
	$(RUN) ./gen_routes/gen_routes.sh
	@touch $(BUILD)/.routes

$(BUILD)/.scenarios: | $(BUILD)
	@echo "Generating scenarios"
	$(RUN) ./gen_scenarios/gen_scenarios.sh
	@touch $(BUILD)/.scenarios


$(BUILD):
	mkdir -p $(BUILD)

.PHONY: clean
clean:
	rm -rf $(BUILD)
