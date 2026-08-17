.PHONY: zip verify tokens link

##@ Complemento

zip: ## Empaquetar el complemento para instalar en QGIS
	@$(LIB)
	banner 'ZIP' 'complemento de QGIS'
	rule
	./scripts/build-zip.sh

verify: ## Comprobar que el zip coincide con el repositorio
	@$(LIB)
	banner 'VERIFY' 'zip contra repositorio'
	rule
	./scripts/verify-zip.sh

tokens: ## Traer el theme.qss del modulo Identidad de mariachi
	@$(LIB)
	banner 'TOKENS' 'identidad visual'
	rule
	./scripts/sync-tokens.sh $(ARCHIVO)

link: ## Enlazar este repositorio al perfil de QGIS para desarrollo
	@$(LIB)
	banner 'LINK' 'perfil de QGIS'
	rule
	destino="$(HOME)/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mapalab"
	if [ -e "$$destino" ] && [ ! -L "$$destino" ]; then
	    fail "Ya hay una carpeta real en $$destino"
	fi
	ln -sfn "$(CURDIR)" "$$destino"
	echo "  $$destino -> $(CURDIR)"
