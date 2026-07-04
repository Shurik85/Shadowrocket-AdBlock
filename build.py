import os
import struct
import urllib.request
import subprocess

# Ссылка на оригинальный geosite.dat, которую ты давал
GEOSITE_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat"

CONFIG = {
    'direct.list': ['category-ru', 'apple', 'category-ip-geo-detect'],
    'proxy.list': ['instagram', 'meta', 'youtube', 'category-ai-!cn', 'category-media-ru-blocked', 'telegram', 'github'],
    'block.list': ['category-ads']
}

def download_file(url, filename):
    print(f"Скачивание {filename}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
        out_file.write(response.read())

def parse_geosite_dat(filename):
    """
    Парсит v2ray geosite.dat без использования сторонних утилит,
    используя сгенерированный на лету protobuf класс.
    """
    # Создаем временную схему v2ray protobuf для парсинга
    proto_content = """
    syntax = "proto3";
    package v2ray.core.app.router;

    message Domain {
      enum Type {
        Plain = 0;
        Regex = 1;
        Domain = 2;
        Full = 3;
      }
      Type type = 1;
      string value = 2;
    }

    message SiteList {
      string tag = 1;
      repeated Domain domain = 2;
    }

    message SiteListCollection {
      repeated SiteList error_list = 1;
    }
    """
    with open("v2ray.proto", "w") as f:
        f.write(proto_content)

    # Компилируем протобуф (в Ubuntu на GitHub Actions protoc уже доступен)
    subprocess.run(["protoc", "--python_out=.", "v2ray.proto"], check=True)
    
    import v2ray_pb2
    
    with open(filename, "rb") as f:
        data = f.read()

    collection = v2ray_pb2.SiteListCollection()
    collection.ParseFromString(data)

    db = {}
    for site_list in collection.error_list:
        tag = site_list.tag.lower()
        db[tag] = []
        for d in site_list.domain:
            # Превращаем типы protobuf в формат Shadowrocket
            if d.type == v2ray_pb2.Domain.Full:
                db[tag].append(f"DOMAIN,{d.value}")
            elif d.type == v2ray_pb2.Domain.Domain:
                db[tag].append(f"DOMAIN-SUFFIX,{d.value}")
            elif d.type == v2ray_pb2.Domain.Plain:
                db[tag].append(f"DOMAIN-KEYWORD,{d.value}")
            elif d.type == v2ray_pb2.Domain.Regex:
                # Пропускаем регулярки
                continue
    
    # Чистим сгенерированные файлы сборщика
    for f in ["v2ray.proto", "v2ray_pb2.py"]:
        if os.path.exists(f):
            os.remove(f)
            
    return db

def main():
    download_file(GEOSITE_URL, "geosite.dat")
    
    print("Парсинг базы данных geosite.dat...")
    db = parse_geosite_dat("geosite.dat")
    
    for output_file, categories in CONFIG.items():
        print(f"--- Формирование файла {output_file} ---")
        written_rules = set()
        
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for cat in categories:
                cat_lower = cat.lower()
                if cat_lower in db:
                    for rule in db[cat_lower]:
                        if rule not in written_rules:
                            outfile.write(f"{rule}\n")
                            written_rules.add(rule)
                else:
                    print(f"Предупреждение: Категория '{cat}' не найдена в базе!")
                    
        print(f"Файл {output_file} успешно создан. Записано правил: {len(written_rules)}")

    if os.path.exists("geosite.dat"):
        os.remove("geosite.dat")

if __name__ == "__main__":
    main()
