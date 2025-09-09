import openai
import random
import requests
from datetime import datetime
import threading
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
from database import get_user_city
from requests import request
import random
import requests
from bs4 import BeautifulSoup
# Configurações
openai.api_key = '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'
API_KEY_OPENWEATHER = '4f767637cb5cac126e3ae075b0051f2a'
CIDADE = 'Canindé de São Francisco'

# Estado do sistema
system_state = {
    'irrigation': False,
    'auto_mode': False,
    'soil_moisture': None,
    'temperature': None,
    'weather': None,
    'humidity': None,
    'clouds' : None,
    'pressure' : None,
    'sunrise' : None,
    'sundown' : None,
    'wind' : None,
    'gust' : None,
    'last_response': '',
    'tts_enabled': True,
    'voice_control': False,
    'last_notification': None,
    'previous_temp': None,
    'previous_moisture': None,
    'notification_sound': 'notification.mp3'
}

climate_forecast = {
    #===MÁXIMAS===
    'max_temp_day1' : None,
    'max_temp_day2' : None,
    'max_temp_day3' : None,
    'max_temp_day4' : None,
    'max_temp_day5' : None,
    #===MÍNIMAS===
    'min_temp_day1' : None,
    'min_temp_day2' : None,
    'min_temp_day3' : None,
    'min_temp_day4' : None,
    'min_temp_day5' : None,

    #---CLIMAS---
    'weather1' : None,
    'weather2' : None,
    'weather3' : None,
    'weather4' : None,
    'weather5' : None,

    #---PRECIPITAÇÃO---
    'precipitation1' : None,
    'precipitation2' : None,
    'precipitation3' : None,
    'precipitation4' : None,
    'precipitation5' : None,

    #---VENTOS---
    'wind1' : None,
    'wind2' : None,
    'wind3' : None,
    'wind4' : None,
    'wind5' : None,

    #---DATAS---
    'date1' : None,
    'date2' : None,
    'date3' : None,
    'date4' : None,
    'date5' : None,

    #---DIAS---
    'day1' : None,
    'day2' : None,
    'day3' : None,
    'day4' : None,
    'day5' : None,
}

gpt_functions = [
    {
        "type": "function",
        "function": {
            "name": "enable_irrigation",
            "description": "Ligar sistema de irrigação",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disable_irrigation",
            "description": "Desligar sistema de irrigação",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_soil_moisture",
            "description": "Checar umidade do solo.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_temperature",
            "description": "Checar clima ou temperatura em geral.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "automatic_irrigation",
            "description": "Ligar modo automático",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "data_simulator",
            "description": "Verificar histórico da fazenda ou plantação. Ou seja, verificar o que ocorreu em 1 semana",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        }
    },
    {
    "type": "function",
    "function": {
        "name": "check_weather_forecast",
        "description": "Fornece a previsão climática para os próximos 10 dias.",
        "parameters": {
            "type": "object",
            "properties": {}
        },
    }
},

]
# Funções do sistema

def check_environment_changes():
    try:
        current_temp = system_state.get('temperature', 25)
        current_moisture = system_state.get('soil_moisture', 45)
        messages = []
        
        # Verificação de temperatura
        if system_state['previous_temp'] is not None:
            temp_diff = abs(current_temp - system_state['previous_temp'])
            
            # Limiares ajustados
            if temp_diff >= 2:  # Detecta mudanças de 2°C ou mais
                if current_temp > 30:
                    messages.append(f"Alerta de calor! Temperatura: {current_temp}°C")
                elif current_temp < 21:
                    messages.append(f"Alerta de frio! Temperatura: {current_temp}°C")
        
        # Verificação de umidade
        if system_state['previous_moisture'] is not None:
            moisture_diff = abs(current_moisture - system_state['previous_moisture'])
            
            # Limiares ajustados
            if moisture_diff >= 10:  # Detecta mudanças de 5% ou mais
                if current_moisture < 45:
                    messages.append(f"Solo seco! Umidade: {current_moisture}%")
                    enable_irrigation()
                elif current_moisture > 50:
                    messages.append(f"Solo encharcado! Umidade: {current_moisture}%")
                    disable_irrigation()
        
        # Atualiza histórico
        system_state['previous_temp'] = current_temp
        system_state['previous_moisture'] = current_moisture
        
        return messages
        
    except Exception as e:
        print(f"Erro na verificação ambiental: {str(e)}")
        return []

def get_system_status():
    return system_state

def get_weathers():
    next_weathers()
    return climate_forecast

def enable_irrigation(ser):
    system_state['irrigation'] = True
    ser.write(b'1\n')
    system_state['last_response'] = "Irrigação ligada com sucesso!"

def disable_irrigation(ser):
    system_state['irrigation'] = False
    ser.write(b'2\n')
    system_state['last_response'] = "Irrigação desligada com sucesso!"

def check_soil_moisture(ser):
    ser.write(b'3\n')
    umidade = ser.readline().decode()
    print('UMIDADE =', umidade)
    system_state['soil_moisture'] = umidade
    system_state['last_response'] = f"Umidade do solo: {system_state['soil_moisture']}%"

def check_temperature():
    url = "https://www.accuweather.com/pt/br/canind%C3%A9-de-s%C3%A3o-francisco/41773/current-weather/41773"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"  # Prioriza português
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        def get_detail_value(label, classe):
            details = soup.find_all("div", class_= classe)
            for d in details:
                if label in d.get_text():
                    # assume que o valor é o segundo div
                    return d.find_all("div")[1].get_text(strip=True)
            return None
        # Temperatura atual (ajusta a classe inspecionando no navegador)
        temp = soup.find("div", class_="display-temp").get_text(strip=True)
        
        # Descrição (ex: "Ensolarado", "Parcialmente nublado", etc.)
        phrase = soup.find("div", class_="phrase").get_text(strip=True)
        sunrise = soup.find_all("span", class_="sunrise-sunset__times-value")[0].get_text(strip=True)
        sundown = soup.find_all("span", class_="sunrise-sunset__times-value")[1].get_text(strip=True)

        wind = get_detail_value("Vento", "detail-item spaced-content")
        gust = get_detail_value("Rajadas de vento", "detail-item spaced-content")
        humidity = get_detail_value("Umidade", "detail-item spaced-content")
        clouds = get_detail_value("Nebulosidade", "detail-item spaced-content")
        pressure = get_detail_value("Pressão", "detail-item spaced-content")

        system_state['temperature'] = temp
        system_state['weather'] = phrase
        system_state['humidity'] = humidity
        system_state['clouds'] = clouds
        system_state['wind'] = wind
        system_state['gust'] = gust
        system_state['pressure'] = pressure
        system_state['sunrise'] = sunrise
        system_state['sundown'] = sundown

        print("Temperatura atual:", temp)
        print("Clima:", phrase)
        print("Vento:", wind)
        print("Rajadas de Vento:", gust)
        print("Umidade Relativa do Ar:", humidity)
        print("Nebulosidade:", clouds)
        print("Pressão:", pressure)
        print("Nascer do Sol:", sunrise)
        print("Pôr do Sol:", sundown)

        
    else:
        print("Erro ao acessar:", response.status_code)

def next_weathers():
    url = "https://www.accuweather.com/pt/br/canind%C3%A9-de-s%C3%A3o-francisco/41773/daily-weather-forecast/41773"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"  # Prioriza português
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        def remove_slash(text):
            """
            Remove todas as ocorrências do caractere '/' de uma string.
            """
            return text.replace("/", "")

        #======= MÁXIMAS E MÍNIMAS ========
        max1 = soup.find_all("span", class_="high")[0].get_text(strip=True)
        min1 = soup.find_all("span", class_="low")[0].get_text(strip=True)
        climate_forecast['max_temp_day1'] = max1
        climate_forecast['min_temp_day1'] = min1
        print('Temperatura Máxima:', max1)
        print('Temperatura Mínima:', remove_slash(min1))

        max2 = soup.find_all("span", class_="high")[1].get_text(strip=True)
        min2 = soup.find_all("span", class_="low")[1].get_text(strip=True)
        climate_forecast['max_temp_day2'] = max2
        climate_forecast['min_temp_day2'] = min2
        print('Temperatura Máxima:', max2)
        print('Temperatura Mínima:', remove_slash(min2))

        max3 = soup.find_all("span", class_="high")[2].get_text(strip=True)
        min3 = soup.find_all("span", class_="low")[2].get_text(strip=True)
        climate_forecast['max_temp_day3'] = max3
        climate_forecast['min_temp_day3'] = min3
        print('Temperatura Máxima:', max3)
        print('Temperatura Mínima:', remove_slash(min3))

        max4 = soup.find_all("span", class_="high")[3].get_text(strip=True)
        min4 = soup.find_all("span", class_="low")[3].get_text(strip=True)
        climate_forecast['max_temp_day4'] = max4
        climate_forecast['min_temp_day4'] = min4
        print('Temperatura Máxima:', max4)
        print('Temperatura Mínima:', remove_slash(min4))

        max5 = soup.find_all("span", class_="high")[4].get_text(strip=True)
        min5 = soup.find_all("span", class_="low")[4].get_text(strip=True)
        climate_forecast['max_temp_day5'] = max5
        climate_forecast['min_temp_day5'] = min5
        print('Temperatura Máxima:', max5)
        print('Temperatura Mínima:', remove_slash(min5))



        #========= CLIMAS ==========
        weather1 = soup.find_all("div", class_="phrase")[0].get_text(strip=True)
        weather2 = soup.find_all("div", class_="phrase")[1].get_text(strip=True)
        weather3 = soup.find_all("div", class_="phrase")[2].get_text(strip=True)
        weather4 = soup.find_all("div", class_="phrase")[3].get_text(strip=True)
        weather5 = soup.find_all("div", class_="phrase")[4].get_text(strip=True)

        climate_forecast['weather1'] = weather1
        climate_forecast['weather2'] = weather2
        climate_forecast['weather3'] = weather3
        climate_forecast['weather4'] = weather4
        climate_forecast['weather5'] = weather5

        #========= PRECIPITAÇÃO ==========
        precipitation1 = soup.find_all("div", class_="precip")[0].get_text(strip=True)
        precipitation2 = soup.find_all("div", class_="precip")[1].get_text(strip=True)
        precipitation3 = soup.find_all("div", class_="precip")[2].get_text(strip=True)
        precipitation4 = soup.find_all("div", class_="precip")[3].get_text(strip=True)
        precipitation5 = soup.find_all("div", class_="precip")[4].get_text(strip=True)

        climate_forecast['precipitation1'] = precipitation1
        climate_forecast['precipitation2'] = precipitation2
        climate_forecast['precipitation3'] = precipitation3
        climate_forecast['precipitation4'] = precipitation4
        climate_forecast['precipitation5'] = precipitation5

        #========= VENTOS ==========
        wind1 = soup.find_all("span", class_="value")[2].get_text(strip=True)
        wind2 = soup.find_all("span", class_="value")[7].get_text(strip=True)
        wind3 = soup.find_all("span", class_="value")[11].get_text(strip=True)
        wind4 = soup.find_all("span", class_="value")[15].get_text(strip=True)
        wind5 = soup.find_all("span", class_="value")[19].get_text(strip=True)

        climate_forecast['wind1'] = wind1
        climate_forecast['wind2'] = wind2
        climate_forecast['wind3'] = wind3
        climate_forecast['wind4'] = wind4
        climate_forecast['wind5'] = wind5

        #========= DATAS ==========
        day1 = soup.find_all("span", class_="module-header sub date")[0].get_text(strip=True)
        day2 = soup.find_all("span", class_="module-header sub date")[1].get_text(strip=True)
        day3 = soup.find_all("span", class_="module-header sub date")[2].get_text(strip=True)
        day4 = soup.find_all("span", class_="module-header sub date")[3].get_text(strip=True)
        day5 = soup.find_all("span", class_="module-header sub date")[4].get_text(strip=True)

        climate_forecast['date1'] = day1
        climate_forecast['date2'] = day2
        climate_forecast['date3'] = day3
        climate_forecast['date4'] = day4
        climate_forecast['date5'] = day5

        #========= DIAS ==========
        date1 = soup.find_all("span", class_="module-header dow date")[0].get_text(strip=True).upper()
        date2 = soup.find_all("span", class_="module-header dow date")[1].get_text(strip=True).upper()
        date3 = soup.find_all("span", class_="module-header dow date")[2].get_text(strip=True).upper()
        date4 = soup.find_all("span", class_="module-header dow date")[3].get_text(strip=True).upper()
        date5 = soup.find_all("span", class_="module-header dow date")[4].get_text(strip=True).upper()

        climate_forecast['day1'] = date1
        climate_forecast['day2'] = date2
        climate_forecast['day3'] = date3
        climate_forecast['day4'] = date4
        climate_forecast['day5'] = date5
    else:
        print("Erro ao acessar:", response.status_code)
        

def check_weather_forecast():
    try:
        # Obter coordenadas diretamente do usuário atual
        from app import current_user  # Importe o current_user do app principal
        
        if not current_user.is_authenticated:
            raise Exception("Usuário não autenticado")

        # 1. Buscar coordenadas da cidade
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={current_user.city}&limit=1&appid={API_KEY_OPENWEATHER}"
        geo_response = requests.get(geo_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        
        if not geo_data:
            raise Exception(f"Cidade '{current_user.city}' não encontrada")

        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']

        # 2. Buscar previsão com coordenadas
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY_OPENWEATHER}&units=metric&lang=pt_br"
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        data = forecast_response.json()
        
        forecast = []
        daily_data = {}
        
        # Processamento otimizado
        for entry in data['list']:
            date = datetime.fromtimestamp(entry['dt']).date()
            if date not in daily_data:
                daily_data[date] = {
                    'temps': [],
                    'humidity': [],
                    'conditions': [],
                    'rain': []
                }
            
            daily_data[date]['temps'].append(entry['main']['temp'])
            daily_data[date]['humidity'].append(entry['main']['humidity'])
            daily_data[date]['conditions'].append(entry['weather'][0]['description'].lower())
            daily_data[date]['rain'].append(entry.get('rain', {}).get('3h', 0))

        # Gerar previsão formatada
        for i, (date, values) in enumerate(daily_data.items()):
            if i >= 5:
                break
                
            forecast.append({
                'day': i + 1,
                'date': date.strftime('%Y-%m-%d'),
                'max_temp': round(max(values['temps']), 1),
                'min_temp': round(min(values['temps']), 1),
                'humidity': round(sum(values['humidity'])/len(values['humidity'])),
                'weather': max(set(values['conditions']), key=values['conditions'].count).capitalize(),
                'rain': round(sum(values['rain']), 1)
            })
        
        system_state['weather'] = forecast
        system_state['last_response'] = "Previsão atualizada com sucesso!"

    except Exception as e:
        print(f"Erro crítico na previsão: {str(e)}")
        # Fallback
        system_state['weather'] = [{
            'day': 1,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'max_temp': 28.5,
            'min_temp': 18.3,
            'humidity': 65,
            'weather': 'Ensolarado',
            'rain': 0
        }]

bot_funcs = {
    "enable_irrigation": enable_irrigation,
    "disable_irrigation": disable_irrigation,
    "check_soil_moisture": check_soil_moisture,
    "check_temperature": check_temperature,
    "check_weather_forecast": check_weather_forecast,
}

append_msgs = True
def gpt_interaction(prompt_text, role="user", func_name=None):
    #if not append_msgs:
        #chat_msgs = default_chat_msgs

    new_msg = {"role": role, "content": prompt_text}
    if func_name:
        new_msg["name"] = func_name

    prompt_chat = []
    if append_msgs:
        messages.append(new_msg)
        prompt_chat = messages
    else:
        prompt_chat = messages.copy()
        prompt_chat.append(new_msg)

def handle_gpt_query(prompt, history):
    global messages
    try:
        messages = [{
            "role": "system",
            "content": "Seu nome é AgroSapiens, um assistente virtual que auxilia agricultores de maneira prática e didática. Você conhece todas as técnicas agrícolas e é especialista em auxiliar pequenos agricultores não intusiasmados com a tecnologia. Você pode tocar músicas com sua função de rádio, basta clicar no botão. Sempre inicie perguntando o nome do usuário. Além disso voce tem um botão de desligar a irrigação e ligar, ambos verdes, basta apertar neles no canto superior esquerdo da tela ou apenas pedir para voce. Você também tem os botoes de verificar umidade e o clima proximos aos botoes anteriores. Lembre-se que voce é um ser tecnologico, mas seu publico não é familiarizado. Seja sempre muito simples, o agricultor é muito basico! Responda tudo em até 4 frases"  # Mantenha seu prompt original
        }]
        
        # Adicionar histórico
        for entry in history[-6:]:
            messages.append({"role": entry['role'], "content": entry['content']})
        
        messages.append({"role": "user", "content": prompt})
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=250,
            tools=gpt_functions,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        # Verificar se há chamada de função
        if hasattr(response_message, 'tool_calls'):
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                if function_name in bot_funcs:
                    bot_funcs[function_name]()
                    return system_state['last_response']  # Garanta que isso retorne texto
        
        # Fallback para respostas sem função
        return response_message.get('content', "Desculpe, não entendi. Poderia repetir?")
        
    except Exception as e:
        return f"Erro no processamento: {str(e)}"

def text_to_speech(text):
    try:
        # Gera um nome de arquivo único
        filename = f"tts_{hash(text)}.mp3"
        filepath = f"static/tts/{filename}"
        
        # Cria o diretório se não existir
        os.makedirs("static/tts", exist_ok=True)
        
        # Gera o áudio e salva
        tts = gTTS(text=text, lang='pt-br')
        tts.save(filepath)
        
        return filename  # Retorna o nome do arquivo
        
    except Exception as e:
        print(f"Erro no TTS: {str(e)}")
        return None
