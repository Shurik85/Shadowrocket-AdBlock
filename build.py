import os
import urllib.request

# Базовый URL, откуда мы берем текстовые списки доменов по категориям
BASE_URL = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/master/geosite/"

# Твоя конфигурация категорий
CONFIG = {
    'direct.list': ['category-ru', 'apple', 'category-ip-geo-detect'],
    'proxy.list': ['instagram', 'meta', 'youtube', 'category-ai-!cn', 'category-media-ru-blocked', 'telegram', 'github'],
    'block.list': ['category-ads']
}

def download_category_text(category):
    url = f"{BASE_URL}{category.lower()}.txt"
    print(f"Загрузка категории: {category}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Ошибка при загрузке категории {category}: {e}")
        return []

def parse_line(line):
    """
    Преобразует строку из исходника loyal-soldier в формат Shadowrocket RULE-SET.
    """
    line = line.strip()
    # Пропускаем пустые строки и комментарии
    if not line or line.startswith('#'):
        return None
        
    # В текстовых исходниках loyal-soldier форматы могут быть такими:
    # full:example.com, domain:example.com, keyword:example, regex:...
    # Либо просто домен (по умолчанию для v2ray это суффикс/поддомены)
    
    if line.startswith("full:"):
        domain = line.replace("full:", "").strip()
        return f"DOMAIN,{domain}"
    elif line.startswith("domain:"):
        domain = line.replace("domain:", "").strip()
        return f"DOMAIN-SUFFIX,{domain}"
    elif line.startswith("keyword:"):
        keyword = line.replace("keyword:", "").strip()
        return f"DOMAIN-KEYWORD,{keyword}"
    elif line.startswith("regex:"):
        # Регулярные выражения пропускаем, Shadowrocket RULE-SET их не поддерживает
        return None
    else:
        # Если префикса нет, loyal-soldier подразумевает root-domain со всеми поддоменами
        return f"DOMAIN-SUFFIX,{line}"

def main():
    for output_file, categories in CONFIG.items():
        print(f"--- Формирование файла {output_file} ---")
        written_rules = set()
        
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for cat in categories:
                lines = download_category_text(cat)
                for line in lines:
                    rule = parse_line(line)
                    if rule and rule not in written_rules:
                        outfile.write(f"{rule}\n")
                        written_rules.add(rule)
                        
        print(f"Файл {output_file} успешно создан. Записано правил: {len(written_rules)}")

if __name__ == "__main__":
    main()
