# Monitor de TIIE 28 Días y Tasa Objetivo — BANXICO-SIIE (v0.1)

Una interfaz gráfica ultra-compacta y elegante (tipo widget overlay de Nvidia) desarrollada en Python para el monitoreo en tiempo real de la **Tasa de Interés Interbancaria de Equilibrio (TIIE) a 28 días** diaria y la **Tasa Objetivo** de política monetaria, consumiendo la API oficial de Banco de México (Banxico).

El monitor está diseñado para permanecer fijo por encima de otras ventanas en pantalla, facilitando a analistas financieros, desarrolladores y tomadores de decisiones el acceso rápido al costo del dinero en México.

---

## Características Principales

*   **Diseño Premium Estilo Overlay (Dark Theme)**: Interfaz compacta (310x250px) en gris oscuro translúcido, sin bordes de ventana clásicos para un aspecto moderno y limpio.
*   **Siempre al Frente (Always on Top)**: Flota de forma fija por encima de todas las demás aplicaciones.
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

### 2. Instrucciones de Inicio
Para arrancar el monitor, abre una terminal (PowerShell o cmd) en la carpeta del proyecto y ejecuta:
```powershell
python tiie_monitor.py
```
El widget aparecerá de inmediato en la esquina superior derecha de la pantalla y cargará los datos más recientes.

### 3. Interacciones y Controles

```
+-------------------------------------------------------+
|  TIIE 28 Dias  BANXICO- SIIE              ↻   ─   ×  |  <-- Barra de Controles
+-------------------------------------------------------+
|                                                       |
|  TIIE DIARIA (28 DÍAS)                                |
|  6.7559%   ▼ -0.0402%                                 |  <-- Tarjeta Diaria (Tasa, Tendencia)
|  Ant: 6.7961%  |  Est. Mañana: 6.7610%                |  <-- Meta (Ayer vs Predicción)
|                                                       |
|  ---------------------------------------------------  |  <-- Separador Fino
|                                                       |
|  TASA OBJETIVO BANXICO                                |
|  6.5000%   = Estable                                  |  <-- Tarjeta Tasa Objetivo (Valor, Tendencia)
|  Ant: 6.5000%  |  Est. Siguiente: 6.5000%             |  <-- Meta (Tasa anterior vs Predicción)
|                                                       |
|  ● Act: 11:25:42                           SIE Banxico|  <-- Pie de página (Estado, Origen)
+-------------------------------------------------------+
```

*   **Arrastrar el Widget**: Haz clic izquierdo en el título de la barra superior, en la parte posterior del fondo o en las tarjetas y mueve el mouse para reposicionarlo en cualquier lugar del escritorio.
*   **Recargar los Datos**: Haz clic izquierdo sobre el botón circular `↻` en la barra superior. Verás que el indicador cambia a amarillo `"Actualizando..."` y se refresca.
*   **Minimizar el Widget**: Presiona el botón de la línea `─` en la barra superior o haz clic derecho y selecciona **Minimizar ─**. El widget desaparecerá y se quedará en la barra de tareas de Windows. Haz clic sobre el ícono del script para restaurarlo en la misma posición de pantalla.
*   **Ajustar Transparencia (Opacidad)**: Haz clic derecho sobre el cuerpo del monitor, ve al submenú **Opacidad** y selecciona el porcentaje deseado. La transparencia cambiará inmediatamente.
*   **Configurar Prioridad de Pantalla**: Haz clic derecho y selecciona **Fijar al Frente (Sí/No)** para activar o desactivar que permanezca sobre otras aplicaciones.
*   **Cerrar**: Presiona el botón `×` en la barra superior, o haz clic derecho y selecciona **Cerrar** para apagar el script y su programador de forma limpia.

---

## Detalles Técnicos y Matemáticos

### 1. Consumo del API REST de Banxico
El widget consume de forma conjunta las series **SF43783** (TIIE a 28 días diaria) y **SF61745** (Tasa Objetivo del Banco de México) en una única petición de rango mediante el servicio REST del SIE.
*   Para optimizar la cuota de peticiones y respetar los límites de la API, el monitor solicita el histórico de los últimos 90 días naturales para ambas series de forma simultánea.
*   El protocolo TLS 1.3 se configura explícitamente mediante el contexto SSL de Python (`DEFAULT@SECLEVEL=1`) para evitar errores de comunicación en sistemas Windows antiguos.

### 2. Lógica del Motor de Análisis
*   **Tendencia (Diaria y Tasa Objetivo)**: Se calcula la diferencia aritmética entre el valor observado más reciente ($v_0$) y el de la jornada inmediata anterior ($v_{-1}$):
    $$\Delta = v_0 - v_{-1}$$
    *   $\Delta > 0.00001\% \rightarrow$ Alza (`▲` verde)
    *   $\Delta < -0.00001\% \rightarrow$ Baja (`▼` rojo)
    *   Diferencia insignificante $\rightarrow$ Estable (`=` dorado)
*   **Tasa Objetivo**: Representa la tasa de interés de referencia para las operaciones interbancarias a un día establecidas por la Junta de Gobierno del Banco de México. Al ser una tasa de política monetaria, se mantiene constante por semanas o meses y cambia de forma discreta (+/-0.25% generalmente).
*   **Algoritmo de Predicción (Regresión Lineal)**:
    Se ajusta un modelo por mínimos cuadrados ordinarios $y = mx + c$ sobre las últimas 5 observaciones para preguntar la tasa de la jornada siguiente:
    *   **Tasa Diaria Mañana (TIIE 28d)**: Proyección lineal a partir de la pendiente de los últimos 5 días.
    *   **Tasa Objetivo Siguiente**: Proyección lineal a partir de los últimos 5 días (se mantiene plana a menos que haya habido un cambio muy reciente).

---

## Diagnóstico y Solución de Problemas

En caso de que el widget muestre un estado en rojo en el pie de página, abre el archivo `tiie_monitor.log` en el directorio del proyecto para diagnosticar el problema:
*   `Error de Conexión`: Verifica que tengas salida a internet y que el portal de Banxico esté operativo.
*   `HTTP Error 401 / 400`: El token de consulta ha expirado o se ha configurado mal el identificador de la serie.
*   `Error de Datos`: La estructura JSON devuelta por Banxico cambió.

---

## Licencia y Uso
Este software es una herramienta utilitaria de código abierto para monitoreo financiero. Todos los datos financieros mostrados son propiedad intelectual del Banco de México (Banxico) y se obtienen únicamente con fines informativos.
