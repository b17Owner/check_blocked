# check_blocked
Проверка запрёщенных url/ip/domain по списку РКН

    usage: check_blocked.py [-h] [-d] [-c CONFIG] [-f FILE] [-r RESPONSE]
    
    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           enable debug
      -c CONFIG, --config CONFIG
                            config file (default: .env)
      -f FILE, --file FILE  filename with url/domain/ip list
      -r RESPONSE, --response RESPONSE
                            response url from blocked page


## Запуск в docker
Переименуйте файл example.env в .env, заполните нужные параметры

    docker-compose build && docker-compose up -d
    
  
## Запуск локально

### Подготовка к запуску

    python3 -m venv venv
    source venv/bin/activate
    pip3 install requests python-dotenv

### Запуск приложения
    cd app && python3 app/check_blocked.py
