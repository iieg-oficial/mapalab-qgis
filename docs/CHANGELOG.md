# Changelog

Todos los cambios notables del complemento se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/).

El complemento nacio dentro del repositorio del visor, en `mapalab/plugin/`, y se separo el
2026-08-17 conservando su historial. Las versiones hasta la 0.14.0 estan documentadas en el
CHANGELOG de aquel repositorio, entre sus versiones 1.117.0 y 1.128.1.

---

## [0.17.0] - 2026-10-16

Listo para el repositorio oficial de complementos de QGIS. Probado en QGIS 3.40 y 4.0.

### Agregado

- **Soporte de QGIS 4** (Qt 6): enums con su nombre completo, `QMetaType` en lugar de `QVariant`,
  `exec()`, posicion del mouse compatible y `QSvgWidget` desde `QtSvgWidgets` cuando hace falta. El
  mismo codigo corre en 3.40 y en 4.x; `qgisMaximumVersion=4.99`.
- `make scan`: corre sobre el zip Bandit y detect-secrets, los escaneres que bloquean una version en
  el repositorio oficial, y flake8 como informe.
- README en ingles con instalacion, uso y requisitos, y GIFs de la busqueda con filtros, la consulta
  por clic y los mapas compartidos.

### Cambiado

- `metadata.txt` con descripcion en ingles, el changelog de las ultimas versiones y
  `experimental=True` para la primera publicacion.
- `make tokens` toma la direccion del `tokens.qss` de `TOKENS_URL` y su token de `TOKENS_AUTH`; ya no
  hay rutas de servicios internos en el repositorio.
- El boton de ayuda de los filtros se ve como un circulo con «?».
- El servidor viene configurado como `https://iieg.jalisco.gob.mx`: el panel carga el catalogo al
  abrirse sin preguntar. Otro servidor se pone desde «Cambiar servidor…».

### Corregido

- Bandit marcaba dos hallazgos altos por SHA-1 en los nombres de la cache; se declara
  `usedforsecurity=False`, porque no protege nada.

---

## [0.16.0] - 2026-10-16

Probado en QGIS 3.40.

### Agregado

- **Filtro por municipio y por fecha** debajo del arbol. Municipio aparece si la capa declara su
  campo (`searchMeta.municipioField`), con boton ZMG; fecha, si `/periodicity` trae periodos o si es
  un raster con `timeEnabled`. Arranca en el periodo del visor (`defaultDate`: el ultimo mes con
  `latest`, el ano completo con `{year}`). Cambiar el filtro actualiza la capa ya cargada y su
  nombre («Feminicidios (tasa) · ago 2026 · ZMG»). Aplica tambien a la consulta por clic y a la
  descarga, que guarda el periodo y los municipios en el nombre del archivo. En grupos solo aplica
  el municipio, y cambiarlo rearma el grupo.
- Los rasters con dimension `TIME` mandan `TIME=AAAA-MM-01` y su estilo del mes (`timeStylePattern`).
- **Abrir mapa compartido** (menu Web → MapaLab y boton del panel): acepta el enlace del visor
  (`?s=` o `?share=`) o el codigo de 10 letras, muestra las capas antes de agregarlas y las monta en
  un grupo «Mapa compartido · <codigo>» con su orden, visibilidad, opacidad, filtros, municipios y
  limites IIEG/INEGI; encuadra la vista y trae opcionalmente un mapa base y las anotaciones (texto
  plano). El mapa base es OpenStreetMap: los raster de CARTO piden llave y sin ella llegan con
  marca de agua. De un compartido de dos paneles toma el activo. Si una capa con fecha por defecto
  llega sin fecha, se aplica la del visor en vez de dibujarla vacia.

### Cambiado

- Las capas temporales ya no entran con todos los periodos encimados: entran con el del visor.

---

## [0.15.0] - 2026-10-16

Revision completa del complemento. Probado en QGIS 3.40.

### Agregado

- **Cambiar servidor** en el menu Web → MapaLab: vuelve a mostrar la direccion sin tocar las
  opciones avanzadas. Al guardarla se descartan el arbol y los iconos del servidor anterior.
- Aviso de **catalogo sin conexion** cuando el servidor no responde y se muestra el ultimo guardado.

### Cambiado

- La red sale del hilo de la interfaz: logos, iconos y el icono de la barra se precargan en la tarea
  del catalogo y la interfaz solo lee la cache; la metadata y la consulta por clic corren en tarea.
- La cache de assets expira a los 7 dias, recuerda los fallos un dia y no sale a otro servidor que el
  configurado (antes caia a los de produccion).
- La cache del catalogo es una por servidor y se escribe de forma atomica.
- La consulta por clic toma el panel solo si la herramienta activa es la mano o identificar; al
  ocultarse devuelve la mano. Elegir una capa del arbol la vuelve a activar.
- El buscador espera 200 ms antes de rehacer el arbol, y el arbol ya no lee `theme.qss` ni recorre
  el proyecto en cada repintado.
- El switch IIEG | INEGI agrega los limites nuevos antes de quitar los otros y deshace lo agregado
  si algo falla.
- En un grupo, la capa que junta varias hojas de una tabla ya no lleva el `nodeId` de la primera.
- `X-Mapalab-Client` lleva la version de `metadata.txt`.

### Corregido

- **La metadata casi no se llenaba**: se leian claves que el backend no publica. Ahora entran
  frecuencia, ultima actualizacion, metodologia, leyenda juridica, fuentes y sus enlaces; los
  derechos mostraban el repr de un diccionario de Python.
- **Descargar otra vez sobrescribia el GeoPackage**, aunque estuviera editado o abierto, y una
  respuesta de error lo truncaba y borraba. Ahora se valida antes de escribir y la segunda descarga
  se guarda como `<nombre>_2.gpkg`. Si GeoServer responde una excepcion, se muestra su texto.
- **Cerrar el panel cancelaba la descarga** sin avisar. Ahora solo se cancela al descargar el
  complemento, y la cancelacion se reporta.
- **La consulta sobre capas cargadas no servia**: QGIS pedia GML 3.1.1, no leia los atributos y
  numeraba todo con id 0, asi que el segundo clic se tomaba por el primero. Ahora todas las
  consultas piden JSON con el filtro y el `ENV` de la capa.
- Las capas deshabilitadas ya no se agregan desde el clic derecho.
- Un grupo cuyo filtro combinado es demasiado largo avisa que trae la tabla completa; ya no deja
  grupos vacios en el proyecto si ninguna capa entra.
- Agregar dos veces la misma capa con el mismo filtro la activa en vez de duplicarla.
- La consulta sin capa elegida ignora los limites si hay capas tematicas visibles.
- Los errores 4xx muestran el inicio de la respuesta del servidor.
- La capa de seleccion acepta `Polygon` y `MultiPolygon` de la misma capa.

---

## [0.14.2] - 2026-09-02

### Cambiado: `make tokens` sigue la nueva ruta del manual de identidad

`scripts/sync-tokens.sh` sigue la ruta nueva de donde se publica el `theme.qss`; el contenido no
cambia.

---

## [0.14.1] - 2026-08-28

### Corregido: el estado «deshabilitada» se lee del arbol, no de la primera letra del nombre

`is_disabled()` daba por deshabilitada a toda capa cuyo `label` empezara con `*`. Desde la 1.146.0
del visor ese asterisco ya no existe: el arbol publica `disabled: true`. El complemento acepta las
dos formas, porque esta instalado en maquinas que no se actualizan a la vez que el servidor y
tiene que funcionar contra cualquiera de las dos versiones.

`clean_label()` se queda como esta: con el arbol nuevo no tiene nada que quitar, y con el viejo
sigue haciendo falta.

---

## [0.14.0] - 2026-08-17

### Cambiado: la simbologia sigue al visor y al catalogo de identidad

Los cuatro glifos de geometria del arbol comparten el naranja `accent-deep`, que se lee del
`theme.qss` que se genera desde el manual de identidad en vez de estar escrito en el codigo, y el
de poligono paso de pentagono a triangulo: el hexagono queda reservado al modo hexbin del visor.

`make tokens` trae ese `theme.qss` cuando la identidad cambia, en lugar de copiarlo a mano.

### Cambiado: una sola limpieza en el panel

Queda «Limpiar seleccionados», que retira las capas de seleccion que deja la consulta por clic.
El «Limpiar» que se llevaba todo se retiro: cada capa ya se quita con su aspa y cada grupo con su
casilla.
