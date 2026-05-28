# Monitor de TIIE 28 Días, Tasa Objetivo y Expectativas — BANXICO-SIIE (v0.2)

Una interfaz gráfica ultra-compacta y elegante (tipo widget overlay de Nvidia) desarrollada en Python para el monitoreo en tiempo real de la **Tasa de Interés Interbancaria de Equilibrio (TIIE) a 28 días** diaria, la **Tasa Objetivo** de política monetaria, y las **Expectativas de la Encuesta de Cetes a 28 días** al cierre del año actual y siguiente, consumiendo la API oficial de Banco de México (Banxico).

El monitor está diseñado para permanecer fijo por encima de otras ventanas en pantalla, facilitando a analistas financieros, desarrolladores y tomadores de decisiones el acceso rápido al costo del dinero y a sus proyecciones futuras en México.

<img width="364" height="592" alt="image" src="https://github.com/user-attachments/assets/1f10ab13-f20f-4916-b997-759a74c8dc43" />


---

## Características Principales

*   **Diseño Premium Estilo Overlay (Dark Theme)**: Interfaz compacta (350x580px) en gris oscuro translúcido, sin bordes de ventana clásicos para un aspecto moderno y limpio.
*   **Siempre al Frente (Always on Top)**: Flota de forma fija por encima de todas las demás aplicaciones.
*   **Gráfica de Vectores en Canvas (Zero-Dependencies)**:
    *   **Historial (Últimos 30 días hábiles)**: Línea continua blanca con la evolución real de la TIIE a 28 días.
    *   **Proyección (Siguientes 12 meses)**: Corredor que se expande a partir de la fecha actual mostrando la Media proyectada (línea azul continua), el Máximo esperado (línea punteada roja) y el Mínimo esperado (línea punteada verde).
*   **Tabla de Proyección Copiable**:
    *   Muestra los 12 meses siguientes ordenados cronológicamente con sus valores mínimos, medios y máximos esperados.
    *   **Selección Manual**: Es un widget de texto nativo que permite seleccionar cualquier fila o rango de texto con el cursor y copiarlo con `Ctrl+C`.
    *   **Botón de Copiado Rápido 📋**: Copia la tabla completa directamente al portapapeles del sistema en formato de texto plano separado por tabulaciones, listo para ser pegado directamente en Excel, Google Sheets o Notepad conservando la estructura de columnas.
*   **Interactividad Completa**:
    *   **Arrastrar y Soltar**: Haz clic izquierdo y arrastra desde cualquier parte del widget para posicionarlo en la esquina que prefieras.
    *   **Minimizar Nativo**: Botón `─` en el encabezado o clic derecho -> *"Minimizar"* para enviarlo a la barra de tareas de Windows de forma nativa sin perder la configuración flotante.
    *   **Opacidad Dinámica**: Ajusta la transparencia en vivo (25%, 50%, 70%, 85%, 95%, 100%) desde el menú contextual.
    *   **Refresco Manual**: Botón `↻` en el encabezado o clic derecho -> *"Refrescar Ahora"* para forzar una consulta inmediata a la API de Banxico.
*   **Cero Dependencias Complejas**: Desarrollado en Python puro usando exclusivamente su librería estándar (`tkinter`, `urllib`, `threading`, etc.). Carga al instante y no requiere de configuraciones complejas de dependencias externas.
*   **Programador Inteligente en Segundo Plano**: Verifica automáticamente al arrancar y exactamente a las **12:00, 13:00, 14:00, 15:00, 18:00 y 19:00 horas** (horas clave de actualización en Banxico).
*   **Bitácora de Auditoría**: Registra todas las conexiones y operaciones en el archivo local `tiie_monitor.log`.

---

## Guía del Usuario (User Guide)

### 1. Requisitos Previos
*   Tener instalado **Python 3.8 o superior**.
*   Conexión a internet estable.

### 2. Configuración del Token de la API Banxico (SIE)
Para poder consultar la información financiera oficial, el monitor requiere de un token (clave) gratuito de la API del Sistema de Información Económica (SIE) de Banco de México:

1.  **Obtener Token**: Registra tu correo electrónico y obtén tu token gratuito en la [página oficial de Banxico](https://www.banxico.org.mx/SieAPIRest/service/v1/token).
2.  **Configuración en la Primera Ejecución (Recomendada)**: 
    *   Al abrir el monitor por primera vez (ejecutando `python tiie_monitor.py`), aparecerá automáticamente una ventana emergente pidiéndote pegar tu token.
    *   Una vez introducido, el monitor lo guardará automáticamente en un archivo local llamado `banxico_token.txt` y no volverá a pedírtelo.
3.  **Configuración Manual**:
    *   Crea un archivo llamado `banxico_token.txt` en la misma carpeta del script.
    *   Pega tu token en el archivo y guárdalo.
4.  **Uso mediante Variables de Entorno**:
    *   Define una variable de entorno en tu sistema llamada `BANXICO_TOKEN` con el valor de tu token.
5.  **Cambiar o Actualizar el Token**:
    *   Si requieres cambiar tu token, haz clic derecho sobre cualquier parte del monitor, selecciona **"Configurar Token 🔑"**, ingresa la nueva clave en la ventana flotante y presiona Aceptar. Los datos se actualizarán al instante.



### 3. Instrucciones de Inicio
Para arrancar el monitor, abre una terminal (PowerShell o cmd) en la carpeta del proyecto y ejecuta:
```powershell
python tiie_monitor.py
```
El widget aparecerá de inmediato en la esquina superior derecha de la pantalla y cargará los datos más recientes.

### 3. Interacciones y Controles

*   **Arrastrar el Widget**: Haz clic izquierdo en el título de la barra superior, en la parte posterior del fondo o en las tarjetas y mueve el mouse para reposicionarlo en cualquier lugar del escritorio.
*   **Recargar los Datos**: Haz clic izquierdo sobre el botón circular `↻` en la barra superior. Verás que el indicador cambia a amarillo `"Actualizando..."` y se refresca.
*   **Minimizar el Widget**: Presiona el botón de la línea `─` en la barra superior o haz clic derecho y selecciona **Minimizar ─**. El widget desaparecerá y se quedará en la barra de tareas de Windows. Haz clic sobre el ícono del script para restaurarlo en la misma posición de pantalla.
*   **Copiar los Datos a Excel**: Haz clic sobre el botón **"Copiar Tabla 📋"** ubicado arriba del cuadro de texto. El botón cambiará temporalmente a `"Copiado! ✓"` en verde y ya podrás pegar los datos tabulados en una hoja de cálculo con `Ctrl+V`.
*   **Ajustar Transparencia (Opacidad)**: Haz clic derecho sobre el cuerpo del monitor, ve al submenú **Opacidad** y selecciona el porcentaje deseado. La transparencia cambiará inmediatamente.
*   **Configurar Prioridad de Pantalla**: Haz clic derecho y selecciona **Fijar al Frente (Sí/No)** para activar o desactivar que permanezca sobre otras aplicaciones.
*   **Cerrar**: Presiona el botón `×` en la barra superior, o haz clic derecho y selecciona **Cerrar** para apagar el script y su programador de forma limpia.

---

## Detalles Técnicos y Matemáticos

### 1. Consumo del API REST de Banxico
El widget consume de forma conjunta las series de la TIIE, la Tasa Objetivo y la Encuesta de Expectativas en una única petición REST:
*   `SF43783`: TIIE a 28 días diaria.
*   `SF61745`: Tasa Objetivo.
*   `SR14748` / `SR14752` / `SR14753`: Media, Mínimo y Máximo esperados para Cetes 28d al cierre del año actual $t$.
*   `SR14755` / `SR14759` / `SR14760`: Media, Mínimo y Máximo esperados para Cetes 28d al cierre del año siguiente $t+1$.

### 2. Modelo de Pronóstico (Interpolación Lineal)
Para trazar la proyección de las tasas en los siguientes 12 meses a partir de la fecha de hoy (Mes 0), calculamos dinámicamente la distancia en meses hacia los dos puntos de control provistos por la encuesta de Banxico:
1.  **Mes $D_1$ (Diciembre de este año)**: Distancia calculada como $12 - \text{mes\_actual}$.
2.  **Mes $D_2$ (Diciembre del año siguiente)**: Distancia calculada como $D_1 + 12$.

Con estos puntos, aplicamos una interpolación lineal de tres tramos para cada uno de los 12 meses proyectados ($m$):
*   Si $m \le D_1$:
    $$\text{Tasa}_m = \text{Tasa}_{\text{hoy}} + \frac{m}{D_1} \times (\text{Expectativa}_t - \text{Tasa}_{\text{hoy}})$$
*   Si $m > D_1$:
    $$\text{Tasa}_m = \text{Expectativa}_t + \frac{m - D_1}{12} \times (\text{Expectativa}_{t+1} - \text{Expectativa}_t)$$

*(En caso de que el mes actual sea Diciembre ($D_1 = 0$), el tramo de control se simplifica interpolando directamente hacia diciembre del año siguiente).*

---

## Diagnóstico y Solución de Problemas

En caso de que el widget muestre un estado en rojo en el pie de página, abre el archivo `tiie_monitor.log` en el directorio del proyecto para diagnosticar el problema:
*   `Error de Conexión`: Verifica que tengas salida a internet y que el portal de Banxico esté operativo.
*   `HTTP Error 401 / 400`: El token de consulta ha expirado o se ha configurado mal el identificador de la serie.
*   `Error de Datos`: La estructura JSON devuelta por Banxico cambió.

---

## Licencia y Uso
Este software es una herramienta utilitaria de código abierto para monitoreo financiero. Todos los datos financieros mostrados son propiedad intelectual del Banco de México (Banxico) y se obtienen únicamente con fines informativos.
