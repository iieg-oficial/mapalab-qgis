# Changelog

Todos los cambios notables del complemento se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/).

El complemento nacio dentro del repositorio del visor, en `mapalab/plugin/`, y se separo el
2026-08-17 conservando su historial. Las versiones hasta la 0.14.0 estan documentadas en el
CHANGELOG de aquel repositorio, entre sus versiones 1.117.0 y 1.128.1.

---

## [0.14.2] - 2026-09-02

### Cambiado: `make tokens` apunta al modulo MEL

El modulo Identidad de mariachi se renombro a MEL (Manual de Estilo y Lineamientos) y su prefijo de
API paso de `/identidad` a `/mel`. `scripts/sync-tokens.sh` sigue esa ruta. El `theme.qss` que trae
declara ahora su origen como MEL en el encabezado; el contenido no cambia.

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
`theme.qss` que emite el modulo Identidad de mariachi en vez de estar escrito en el codigo, y el
de poligono paso de pentagono a triangulo: el hexagono queda reservado al modo hexbin del visor.

`make tokens` trae ese `theme.qss` cuando la identidad cambia, en lugar de copiarlo a mano.

### Cambiado: una sola limpieza en el panel

Queda «Limpiar seleccionados», que retira las capas de seleccion que deja la consulta por clic.
El «Limpiar» que se llevaba todo se retiro: cada capa ya se quita con su aspa y cada grupo con su
casilla.
