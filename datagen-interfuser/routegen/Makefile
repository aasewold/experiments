
BUILD := build

.PHONY: route_configs copy

route_configs: $(BUILD)/.route_configs

copy:
	@echo "Copying routes to dest"
	mkdir -p ../idun/files/input
	cp -rf $(BUILD)/output/* ../idun/files/input/

copy_vcxr:
	@echo "Copying routes to dest"
	mkdir -p ../vcxr/files/input
	cp -rf $(BUILD)/output/* ../vcxr/files/input/

$(BUILD)/.route_configs: | $(BUILD)
	@echo "Generating route_configs"
	python src/generate_route_configs.py
	@touch $(BUILD)/.route_configs


$(BUILD):
	mkdir -p $(BUILD)/output

.PHONY: clean
clean:
	rm -rf $(BUILD)
