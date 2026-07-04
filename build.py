import os
import urllib.request
import subprocess

# Ссылка на geosite.dat, которую ты указал
GEOSITE_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat"

# Конфигурация по твоим требованиям
CONFIG = {
    'direct.list': ['category-ru', 'apple', 'category-ip-geo-detect'],
    'proxy.list': ['instagram', 'meta', 'youtube', 'category-ai-!cn', 'category-media-ru-blocked', 'telegram', 'github'],
    'block.list': ['category-ads']
}

def download_file(url, filename):
    print(f"Скачивание {filename}...")
    # Добавляем User-Agent, чтобы GitHub не блокировал частые запросы скрипта
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
        out_file.write(response.read())

def install_v2dat():
    print("Установка утилиты v2dat...")
    subprocess.run(["go", "install", "github.com/uraimo/v2dat@latest"], check=True)
    os.environ["PATH"] += os.pathsep + os.path.expanduser("~/go/bin")

def parse_geosite_line(line):
    """
    Парсит типы записей из v2dat и переводит их в формат правил Shadowrocket RULE-SET.
    В RULE-SET файлах каждая строка имеет вид: ТИП,ЗНАЧЕНИЕ
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
        
    # Обработка префиксов v2dat
    if line.startswith("full:"):
        domain = line.replace("full:", "")
        return f"DOMAIN,{domain}"
    elif line.startswith("domain:"):
        domain = line.replace("domain:", "")
        return f"DOMAIN-SUFFIX,{domain}"
    elif line.startswith("keyword:"):
        keyword = line.replace("keyword:", "")
        return f"DOMAIN-KEYWORD,{keyword}"
    elif line.startswith("regex:"):
        # Регулярные выражения пропускаем или можно перевести в DOMAIN-KEYWORD, если они простые
        return None
    else:
        # Если префикса нет, по умолчанию v2ray трактует это как sub-domain (совпадает домен и поддомены)
        return f"DOMAIN-SUFFIX,{line}"

def build_rules():
    install_v2dat()
    download_file(GEOSITE_URL, "geosite.dat")
    
    # Собираем все уникальные категории, которые нужно извлечь
    all_tags = []
    for tags in CONFIG.values():
        all_tags.extend(tags)
    # v2dat чувствителен к регистру (в базе они обычно в нижнем регистре)
    all_tags = [tag.lower() for tag in set(all_tags)]
    
    tmp_dir = "./tmp_unpack"
    os.makedirs(tmp_dir, exist_ok=True)
    
    print(f"Распаковка категорий: {all_tags}...")
    cmd = ["v2dat", "unpack", "geosite", "-f", "geosite.dat", "-o", tmp_dir] + all_tags
    subprocess.run(cmd, check=True)
    
    # Формируем итоговые файлы списков
    for output_file, tags in CONFIG.items():
        print(f"Создание файла {output_file}...")
        written_lines = set() # Чтобы избежать дубликатов правил в одном файле
        
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for tag in tags:
                tag_file = os.path.join(tmp_dir, f"geosite_{tag.lower()}.txt")
                if os.path.exists(tag_file):
                    with open(tag_file, 'r', encoding='utf-8') as infile:
                        for line in infile:
                            formatted_rule = parse_geosite_line(line)
                            if formatted_rule and formatted_rule not in written_lines:
                                outfile.write(f"{formatted_rule}\n")
                                written_lines.add(formatted_rule)
                else:
                    print(f"Предупреждение: файл для категории {tag} не найден.")
                    
    # Очистка
    subprocess.run(["rm", "-rf", tmp_dir])
    os.remove("geosite.dat")
    print("Сборка списков успешно завершена!")

if __name__ == "__main__":
    build_rules()
