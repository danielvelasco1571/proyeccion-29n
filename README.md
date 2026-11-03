# Proyección 29N

Modelo de simulación de las elecciones generales del 29 de noviembre de 2026: agregado de encuestas (filtro de Kalman con efecto casa), 25 escenarios, 10.000 simulaciones de Monte Carlo con D'Hondt por circunscripción, mapas provincial, municipal y censal, vista por bloques ideológicos y visor calle a calle de las secciones censales.

La página (`index.html`) es estática. Al abrirse lee `encuestas_nuevas.json` y recalcula todo el modelo en el navegador. Una acción de GitHub actualiza ese archivo cada 30 minutos con las encuestas nuevas que publican Objetivo 176 (ciento76.es) y Wikipedia, incluidas las de ElectoPanel/Electomanía.

## Puesta en marcha (una sola vez)

1. Crea un repositorio **público** en GitHub, por ejemplo `proyeccion-29n`.
2. Sube todo el contenido de esta carpeta, incluida la carpeta oculta `.github`. Si la subida por la web no incluye `.github`, crea el archivo a mano: *Add file → Create new file*, nombre `.github/workflows/actualizar.yml`, y pega el contenido del archivo del mismo nombre.
3. *Settings → Pages*: en *Build and deployment* elige *Deploy from a branch*, rama `main`, carpeta `/ (root)`, y guarda.
4. *Settings → Actions → General → Workflow permissions*: marca *Read and write permissions* y guarda.
5. *Actions → Actualizar encuestas → Run workflow* para probarlo. Si hay encuestas nuevas, verás un commit «Encuestas nuevas …».

La web quedará en `https://TU-USUARIO.github.io/proyeccion-29n/`.

## Archivos

- `index.html`: el visor completo, con los datos de base incluidos (encuestas hasta el 30-10-2026, resultados 2023/2024 por mesa, cartografía).
- `encuestas_nuevas.json`: encuestas añadidas después del 30-10-2026. Se puede editar a mano: cada encuesta lleva `id` (fecha-encuestadora), `fecha`, `casa`, `medio`, `n`, `estado` (`modelo`, `repite`, `CIS`, `partidista`, `agregador`) y los porcentajes `PP`, `PSOE`, `VOX`, `FA`, `COMPROMIS`, `PODEMOS`, `SALF`, `ERC`, `JUNTS`, `BILDU`, `PNV`, `BNG`, `CC`, `UPN`, `AA`.
- `scripts/actualizar_encuestas.py`: el actualizador (Python 3 + beautifulsoup4).
- `.github/workflows/actualizar.yml`: la programación de la actualización.
- `justificacion_modelo_29N.pdf`: justificación metodológica.

## Notas

- Electomanía bloquea las descargas automáticas; sus sondeos llegan a través de Objetivo 176 y Wikipedia en pocas horas.
- GitHub Pages puede tardar unos minutos en servir la versión nueva del JSON tras cada commit.
- La actualización corre en los minutos 7 y 37 de cada hora; GitHub puede retrasar las ejecuciones programadas unos minutos.
- `geo/secc_hd/` guarda la cartografía de secciones con más detalle para el visor calle a calle (callejero © colaboradores de OpenStreetMap).

Web pública: https://danielvelasco1571.github.io/proyeccion-29n/
