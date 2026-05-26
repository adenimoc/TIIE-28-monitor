# Monitor de TIIE 28 Días — BANXICO-SIIE (v0.1)

Una interfaz gráfica ultra-compacta y elegante (tipo widget overlay de Nvidia) desarrollada en Python para el monitoreo en tiempo real de la **Tasa de Interés Interbancaria de Equilibrio (TIIE) a 28 días** (diaria y promedio mensual), consumiendo la API oficial de Banco de México (Banxico).

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
|  TIIE PROMEDIO MENSUAL (20D HÁBILES)                  |
|  6.7725%   ▲ +0.0520%                                 |  <-- Tarjeta Mensual (MA20, Tendencia)
|  Mes Ant: 6.7205%  |  Sig. Est: 6.7750%               |  <-- Meta (Mes anterior vs Predicción)
|                                                       |
|  ● Act: 11:16:41                           SIE Banxico|  <-- Pie de página (Estado, Origen)
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
El widget consume la serie **SF43783** (TIIE a 28 días, diaria en porcentaje anual) mediante el servicio REST del SIE.
*   Para optimizar la cuota de peticiones, el monitor solicita el histórico de los últimos 90 días naturales en una única petición.
*   El protocolo TLS 1.3 se configura explícitamente mediante el contexto SSL de Python (`DEFAULT@SECLEVEL=1`) para evitar errores de comunicación en sistemas Windows antiguos.

### 2. Lógica del Motor de Análisis
*   **Tendencia Diaria**: Se calcula la diferencia aritmética entre la tasa observada más reciente ($t_0$) y la del día hábil inmediato anterior ($t_{-1}$):
    $$\Delta_{\text{diaria}} = t_0 - t_{-1}$$
    *   $\Delta_{\text{diaria}} > 0.00001\% \rightarrow$ Alza (`▲` verde)
    *   $\Delta_{\text{diaria}} < -0.00001\% \rightarrow$ Baja (`▼` rojo)
    *   Diferencia insignificante $\rightarrow$ Estable (`=` dorado)
*   **TIIE Mensual (Promedio)**: Se calcula el promedio simple de las últimas 20 observaciones hábiles (equivalente financiero a un plazo de 28 días naturales de operación):
    $$PM_{\text{actual}} = \frac{1}{20} \sum_{i=0}^{19} t_{-i}$$
*   **Tendencia Mensual**: Compara el promedio del mes actual ($PM_{\text{actual}}$) con el promedio del mes anterior ($PM_{\text{anterior}}$), que abarca de la observación 21 a la 40:
    $$\Delta_{\text{mensual}} = PM_{\text{actual}} - PM_{\text{anterior}}$$
*   **Algoritmo de Predicción (Regresión Lineal)**:
    Se ajusta un modelo por mínimos cuadrados ordinarios $y = mx + c$ sobre las últimas 5 observaciones para proyectar el valor del día siguiente (índice 5):
    *   **Tasa Diaria Mañana**: Proyección directa de la recta de regresión.
    *   **Tasa Mensual Sig. Est**: Se calcula el promedio móvil proyectado reemplazando el valor más antiguo de la ventana por la tasa diaria estimada para mañana.

---

## Diagnóstico y Solución de Problemas

En caso de que el widget muestre un estado en rojo en el pie de página, abre el archivo `tiie_monitor.log` en el directorio del proyecto para diagnosticar el problema:
*   `Error de Conexión`: Verifica que tengas salida a internet y que el portal de Banxico esté operativo.
*   `HTTP Error 401 / 400`: El token de consulta ha expirado o se ha configurado mal el identificador de la serie.
*   `Error de Datos`: La estructura JSON devuelta por Banxico cambió.

---

## Licencia y Uso
Este software es una herramienta utilitaria de código abierto para monitoreo financiero. Todos los datos financieros mostrados son propiedad intelectual del Banco de México (Banxico) y se obtienen únicamente con fines informativos.
