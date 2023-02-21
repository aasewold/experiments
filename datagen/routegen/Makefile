
BUILD := build

.PHONY: routes scenarios

routes: $(BUILD)/.routes
scenarios: $(BUILD)/.scenarios

$(BUILD)/.routes: scenarios | $(BUILD)
	@echo "Generating routes"
	docker compose run --build --rm routegen ./gen_routes/gen_routes.sh
	@touch $(BUILD)/.routes

$(BUILD)/.scenarios: | $(BUILD)
	@echo "Generating scenarios"
	docker compose run --build --rm routegen ./gen_scenarios/gen_scenarios.sh
	@touch $(BUILD)/.scenarios


$(BUILD):
	mkdir -p $(BUILD)

.PHONY: clean
clean:
	rm -rf $(BUILD)
