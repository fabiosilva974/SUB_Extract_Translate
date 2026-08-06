# Documentação e Manutenção do Servidor Linux (GTX 1080)

Este documento serve como base de conhecimento para configurações avançadas e truques para manter o servidor de conversão rodando com desempenho e temperaturas ideais.

## Controle Manual da Ventoinha (Fan Speed) em Modo Headless

Geralmente, quando o Linux roda sem um monitor conectado (modo *headless*), o driver da NVIDIA pode não ativar perfis de ventoinha agressivos automaticamente, fazendo a placa esquentar muito durante o processamento pesado no FFmpeg.

Para forçar o controle manual das ventoinhas (Fan) e baixar a temperatura da GPU, execute a cadeia de comandos abaixo:

```bash
# 1. Cria a configuração permitindo o controle de fan (cool-bits=4) sem precisar de monitor
sudo nvidia-xconfig -a --cool-bits=4 --allow-empty-initial-configuration

# 2. Abre um servidor de tela (X) falso/virtual no background (display :1)
sudo Xorg :1 &

# 3. Ativa o controle manual e seta a velocidade da ventoinha para 80%
DISPLAY=:1 nvidia-settings -a "[gpu:0]/GPUFanControlState=1" -a "[fan:0]/GPUTargetFanSpeed=80"
```

> [!TIP]
> - O valor `80` no final do comando representa **80% de velocidade**. Se a placa ainda estiver muito quente (acima de 80ºC), você pode alterar esse valor para `90` ou `100` para extrair o máximo de refrigeração.
> - Se você reiniciar o servidor Linux, será necessário rodar as linhas 2 e 3 novamente para reativar o controle virtual.

## Controle Automático Inteligente (Curva de Fan Personalizada)

Para não precisar alterar a velocidade da ventoinha manualmente o tempo todo, você pode usar um script que roda em loop monitorando a placa. Conforme a GTX 1080 esquenta (como quando está encodando filmes grandes), ele aumenta o cooler sozinho; quando ela esfria, ele baixa.

O script foi salvo na sua pasta `scripts` com o nome `auto_fan_control.sh`. 

### Código do Script:

```bash
#!/bin/bash

while true; do
    # Captura apenas o número da temperatura
    TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader)
    
    if [ "$TEMP" -ge 80 ]; then
        FAN=85
    elif [ "$TEMP" -ge 70 ]; then
        FAN=65
    else
        FAN=40
    fi

    # Aplica a velocidade no display :1
    DISPLAY=:1 nvidia-settings -a "[gpu:0]/GPUFanControlState=1" -a "[fan:0]/GPUTargetFanSpeed=$FAN" > /dev/null 2>&1
    
    echo "Temp atual: ${TEMP}°C -> Ventoinha ajustada para: ${FAN}%"
    sleep 5
done
```

> [!TIP]
> Para usar, basta garantir que o *Xorg* virtual (passo 2 do comando anterior) esteja rodando, e depois disparar este script. Ele cuidará da saúde térmica da sua placa de forma 100% autônoma!
