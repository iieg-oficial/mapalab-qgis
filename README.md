# MapaLab para QGIS

Complemento que lleva el catálogo del visor [MapaLab](https://iieg.jalisco.gob.mx/mapalab) del
Instituto de Información Estadística y Geográfica de Jalisco a QGIS: el mismo árbol de temas, el
mismo buscador y la misma identidad, sin teclear una URL de WMS ni saber qué es un workspace.

Es de **sólo lectura**. Todo lo que consume ya es público en el visor, así que no pide usuario ni
contraseña; sólo la dirección del servidor, una vez.

## Qué hace

- Trae el catálogo completo y lo muestra como en el visor, con su buscador acento-insensible.
- Agrega capas como **WMS en modo tile**, con el filtro que declara cada nodo del catálogo.
- Descarga cualquier capa vectorial como **GeoPackage** local, ya filtrada.
- **Consulta por clic**: el elemento entra a una capa de selección con su geometría y su ficha.
- Cambia entre los límites **IIEG e INEGI**, que además decide con qué geometría se dibuja todo.

## Instalación

QGIS 3.40 LTR. Descargar el `.zip` de la última versión y en QGIS:
Complementos → Administrar e instalar complementos → **Instalar a partir de ZIP**.

La guía completa vive en la documentación interna del instituto, en Documentación → Plugin QGIS.

## Desarrollo

```bash
make zip                       # empaquetar para instalar
make tokens ARCHIVO=tokens.qss # actualizar la identidad visual
```

Para trabajar sobre el código, enlazar este repositorio en la carpeta de complementos del perfil
de QGIS:

```bash
ln -s "$PWD" ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/mapalab
```

### Ramas

| Rama | Para qué |
|---|---|
| `production` | lo que está publicado |
| `develop` | rama de trabajo; se integra a `production` por PR |
| `tamal-rojo` | ciclo de release en construcción; recibe lo nuevo |

Convenciones del código, versionado y estilo: las del ecosistema IIEG.

## Licencia

MIT. Ver [LICENSE](LICENSE).
