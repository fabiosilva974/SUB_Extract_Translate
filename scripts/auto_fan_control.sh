#!/bin/bash

# Script de Controle Automático de Ventoinha (Fan Curve) para NVIDIA
# Script de Controle de Ventoinha (Fan Curve) para NVIDIA

# Captura apenas o número da temperatura
TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader)

# Curva de Temperatura Granular (Sobe e desce aos poucos)
if [ "$TEMP" -ge 85 ]; then
    FAN=100  # Risco de thermal throttling, força máxima!
elif [ "$TEMP" -ge 80 ]; then
    FAN=85   # Carga muito pesada
elif [ "$TEMP" -ge 75 ]; then
    FAN=75   # Carga pesada
elif [ "$TEMP" -ge 70 ]; then
    FAN=65   # Carga média
elif [ "$TEMP" -ge 60 ]; then
    FAN=55   # Carga leve
elif [ "$TEMP" -ge 50 ]; then
    FAN=45   # Morno / Assistindo vídeo
else
    FAN=35   # Frio / Idle
fi

# Aplica a velocidade no display :1
DISPLAY=:1 nvidia-settings -a "[gpu:0]/GPUFanControlState=1" -a "[fan:0]/GPUTargetFanSpeed=$FAN" > /dev/null 2>&1

# Log opcional para você acompanhar se rodar na mão
echo "Temp atual: ${TEMP}°C -> Ventoinha ajustada para: ${FAN}%"
