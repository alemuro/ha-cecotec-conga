test-local:
	docker run \
		--rm \
		--name homeassistant \
		-v $(shell pwd)/.config:/config \
		-v $(shell pwd)/custom_components:/config/custom_components \
		-p 8123:8123 \
		homeassistant/home-assistant