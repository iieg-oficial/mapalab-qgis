.PHONY: help zip tokens

help: ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

zip: ## Empaquetar el complemento para instalar en QGIS
	./scripts/build-zip.sh

tokens: ## Traer el theme.qss del modulo Identidad de mariachi
	./scripts/sync-tokens.sh $(ARCHIVO)
