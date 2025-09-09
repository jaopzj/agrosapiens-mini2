# 🌱 AgroSapiens-Mini

Protótipo desenvolvido durante o **3º ano do Ensino Médio**, como uma representação em escala reduzida do projeto **AgroSapiens**.  

Este repositório tem como objetivo **versionar e documentar** o progresso do protótipo, que foi inicialmente descontinuado e retomado alguns meses depois.

---

## 📌 Sobre o Projeto

O **AgroSapiens-Mini** é uma **maquete funcional** que simula, em pequena escala, as principais funcionalidades do **AgroSapiens**, uma solução tecnológica voltada para auxiliar agricultores, especialmente os de pequeno e médio porte.  

A proposta é unir **tecnologia acessível** (Arduino, sensores de baixo custo e servidores Python) à **realidade do campo**, oferecendo ferramentas de irrigação, previsão do tempo, gestão agrícola e até mesmo cultura popular via rádios regionais.  

---

## ⚙️ Funcionalidades

### 🌊 Sistema de Irrigação
- Controle de **servo motor** que abre/fecha a comporta de água nas maquetes.  
- Simula um **controle inteligente de irrigação** baseado em sensores de solo.

### 🌱 Monitoramento de Umidade
- Leitura em tempo real via **sensor de umidade do solo**.  
- Possibilidade futura de integrar decisões automáticas de irrigação.

### ☁️ Previsão do Tempo
- Integração com serviços meteorológicos para previsão de até **5 dias**.  
- Pretensão futura de expansão para **30 dias**, com maior precisão e alertas automáticos (chuva, seca, geada).

### 📻 Rádio Rural
- Funções de **rádio online**, que permitem escutar emissoras reais via requisições HTTP.  
- Pensado para agricultores do interior, valorizando a **cultura rural** e aproximando o protótipo da realidade do campo.  

### 🌾 Sistema de Gestão Agrícola *(em desenvolvimento)*
- Edição e registro de dados da lavoura, incluindo:  
  - Plantas jovens  
  - Plantas velhas  
  - Estoque de sementes  
- Futuras melhorias incluem relatórios automáticos e integração com banco de dados.

---

## 🛠️ Tecnologias Utilizadas

- **Arduino UNO** – microcontrolador principal  
- **Linguagem C/C++** – programação embarcada  
- **Servo Motor** – simulação de comporta de irrigação  
- **Sensor de Umidade do Solo** – monitoramento ambiental  
- **Python (Flask)** – servidor backend para integrar previsões do tempo, rádios e sistema agrícola  
- **Python (Web Scraping)** – coleta de dados climáticos via HTML  
- **APIs Climáticas** – previsão de tempo em tempo real  

---

## 🚧 Status do Projeto

⚠️ O código encontra-se em estado **experimental e desorganizado**, pois foi desenvolvido em uma fase inicial do projeto.  
- Algumas funcionalidades estão **completas** (irrigação, leitura de umidade).  
- Outras estão **em protótipo** (rádio, previsão do tempo).  
- E algumas ainda **incompletas** (gestão de lavoura).  

Refatorações e melhorias estão sendo aplicadas gradualmente conforme o versionamento neste repositório.  

---

## ⚠️ Aviso Importante

- Este **NÃO é o projeto oficial do AgroSapiens**.  
- As chaves APIs estão públicas, mas serão revogadas antes de qualquer utilização.  
- Não há previsão de divulgação da versão completa.  
- **Não é autorizada a divulgação ou utilização** do protótipo original e principal sem minha permissão expressa.  

---
