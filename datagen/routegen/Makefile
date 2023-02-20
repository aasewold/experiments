
RESULTS := results

.PHONY: routes scenarios

routes: $(RESULTS)/.routes
scenarios: $(RESULTS)/.scenarios

$(RESULTS)/.routes: scenarios
	@echo "Generating routes"
	docker compose run --build --rm routegen ./gen_routes/gen_routes.sh
	@touch $(RESULTS)/.routes

$(RESULTS)/.scenarios:
	@echo "Generating scenarios"
	docker compose run --build --rm routegen ./gen_scenarios/gen_scenarios.sh
	@touch $(RESULTS)/.scenarios


.PHONY: clean clean-routes clean-scenarios

clean: clean-routes clean-scenarios clean-compose

clean-compose:
	docker compose down

clean-routes:
	@echo "Cleaning routes"
	rm -r $(RESULTS)/routes

clean-scenarios:
	@echo "Cleaning scenarios"
	rm -r $(RESULTS)/scenarios
