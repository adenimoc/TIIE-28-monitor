# Metodología de Cálculos y Pronósticos — Monitor TIIE 28

Este documento explica de forma clara, sencilla y con formalismo matemático las metodologías empleadas por el monitor para generar las predicciones diarias y las proyecciones a 12 meses de la tasa de interés.

---

## 1. Predicción del Siguiente Día Hábil (Regresión Lineal Simple)

Para estimar el valor del día de mañana de la **TIIE Diaria** y de la **Tasa Objetivo**, el sistema analiza el comportamiento reciente a muy corto plazo. 

### El Concepto
Se asume que la tasa sigue una tendencia lineal en el transcurso de la última semana laboral (5 días hábiles). Ajustamos una línea recta que mejor se adapte a estos puntos históricos y la extendemos un paso hacia el futuro.

### La Fórmula
La ecuación de una línea recta es:
$$y = m \cdot x + c$$

Donde:
*   $y$: Es el valor estimado de la tasa de interés.
*   $x$: Es el índice de tiempo (de $0$ a $4$, donde $0$ es hace 4 días y $4$ es el día de hoy).
*   $m$: Es la pendiente de la recta (dirección y velocidad del cambio).
*   $c$: Es la intersección con el eje Y (el punto de partida).

Para encontrar los valores óptimos de la pendiente ($m$) y la intersección ($c$) a partir de nuestras $n = 5$ observaciones reales, aplicamos el método de **Mínimos Cuadrados Ordinarios**:

$$m = \frac{n \sum(x \cdot y) - \sum x \sum y}{n \sum(x^2) - (\sum x)^2}$$

$$c = \frac{\sum y - m \sum x}{n}$$

### La Predicción
Una vez calculados $m$ y $c$, proyectamos la tasa para el día de mañana asignando a $x$ el índice del siguiente periodo ($x = n = 5$):

$$y_{\text{mañana}} = m \cdot 5 + c$$

---

## 2. Proyección de los Siguientes 12 Meses (Interpolación Lineal Multi-tramo)

Para predecir el rumbo de la tasa en los próximos 12 meses, combinamos el dato real observado hoy con las expectativas macroeconómicas de la **Encuesta de Banxico (Cetes a 28 días)** al cierre del año actual y del año siguiente.

### El Concepto
La encuesta de Banxico nos proporciona tres "anclas" o puntos de control en el tiempo:
1.  **Mes 0 (Hoy)**: El valor observado real de la TIIE a 28 días hoy ($T_{\text{hoy}}$).
2.  **Mes $D_1$ (Diciembre de este año)**: La expectativa del cierre del año actual $t$ ($E_t$).
3.  **Mes $D_2$ (Diciembre del año siguiente)**: La expectativa del cierre del año siguiente $t+1$ ($E_{t+1}$).

Para rellenar la tasa de los meses intermedios (del mes 1 al 12), realizamos una transición proporcional y continua utilizando **Interpolación Lineal**.

### Definición de Tiempos
*   $current\_month$: Mes calendario de la fecha actual (ej. Enero = 1, Diciembre = 12).
*   $D_1$: Meses restantes para el cierre de este año:
    $$D_1 = 12 - current\_month$$
*   $D_2$: Meses restantes para el cierre del año siguiente:
    $$D_2 = D_1 + 12$$

### Las Fórmulas de Interpolación
Para calcular la tasa estimada ($T_m$) para cualquier mes futuro $m$ (de $1$ a $12$):

#### Tramo A: Si el mes a proyectar está dentro del año actual ($m \le D_1$)
Se realiza una transición lineal entre la tasa actual ($T_{\text{hoy}}$) y la expectativa de fin de año ($E_t$):
$$T_m = T_{\text{hoy}} + \frac{m}{D_1} \times (E_t - T_{\text{hoy}})$$

#### Tramo B: Si el mes a proyectar pertenece al año siguiente ($m > D_1$)
Se realiza una transición lineal entre la expectativa de fin de año actual ($E_t$) y la del siguiente año ($E_{t+1}$):
$$T_m = E_t + \frac{m - D_1}{12} \times (E_{t+1} - E_t)$$

*(Nota: Si hoy es diciembre, entonces $D_1 = 0$. En este escenario singular, el Tramo A se omite y se interpola directamente hacia el cierre del año siguiente con una distancia de 12 meses).*

---

## 3. Ejemplo Numérico Paso a Paso

Supongamos que realizamos el cálculo en el mes de **Mayo ($current\_month = 5$)** con los siguientes datos obtenidos del API de Banxico:
*   Tasa TIIE diaria hoy ($T_{\text{hoy}}$): **$6.7559\%$**
*   Expectativa Media de Cetes al cierre de año ($E_t$): **$6.5100\%$**
*   Expectativa Media de Cetes al cierre de año siguiente ($E_{t+1}$): **$6.4500\%$**

### Paso A: Determinar distancias
*   Meses para diciembre de este año ($D_1$): $12 - 5 = 7$ meses (Diciembre es el mes 7 de la proyección).
*   Meses para diciembre del próximo año ($D_2$): $7 + 12 = 19$ meses.

### Paso B: Calcular Junio (Mes 1 del pronóstico)
Como $m = 1 \le D_1$ ($1 \le 7$), aplicamos la fórmula del **Tramo A**:
$$T_1 = 6.7559\% + \frac{1}{7} \times (6.5100\% - 6.7559\%)$$
$$T_1 = 6.7559\% + 0.1428 \times (-0.2459\%)$$
$$T_1 = 6.7559\% - 0.0351\% = \mathbf{6.7208\%}$$

### Paso C: Calcular Enero del año siguiente (Mes 8 del pronóstico)
Como $m = 8 > D_1$ ($8 > 7$), aplicamos la fórmula del **Tramo B**:
$$T_8 = 6.5100\% + \frac{8 - 7}{12} \times (6.4500\% - 6.5100\%)$$
$$T_8 = 6.5100\% + \frac{1}{12} \times (-0.0600\%)$$
$$T_8 = 6.5100\% - 0.0050\% = \mathbf{6.5050\%}$$

Este mismo proceso se repite simultáneamente para los valores **Mínimos** y **Máximos** de la encuesta, generando la bandas que delimitan el corredor de expectativas en el gráfico del dashboard.
