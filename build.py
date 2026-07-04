import os
import struct
import urllib.request
import subprocess
import ipaddress

# Ссылки на оригинальные базы
GEOSITE_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat"
GEOIP_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat"

# Конфигурация для Доменов (geosite)
DOMAINS_CONFIG = {
    'direct.list': ['category-ru', 'apple', 'category-ip-geo-detect'],
    'proxy.list': ['instagram', 'meta', 'youtube', 'category-ai-!cn', 'category-media-ru-blocked', 'telegram', 'github'],
    'block.list': ['category-ads']
}

# Конфигурация для IP-адресов (geoip)
IPS_CONFIG = {
    'direct-ip.list': ['ru', 'private'],
    'proxy-ip.list': ['telegram', 'facebook']
}

def download_file(url, filename):
    print(f"Скачивание {filename}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
        out_file.write(response.read())

def generate_protobuf_classes():
    """Создает единую схему protobuf для geosite и geoip и компилирует её."""
    proto_content = """
    syntax = "proto3";
    package v2ray.core.app.router;

    // --- Схема для Geosite ---
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

    // --- Схема для Geoip ---
    message CIDR {
      bytes ip = 1;
      uint32 prefix = 2;
    }

    message GeoIP {
      string country_code = 1;
      repeated CIDR cidr = 2;
    }

    message GeoIPList {
      repeated GeoIP entry = 1;
    }
    """
    with open("v2ray.proto", "w") as f:
        f.write(proto_content)

    subprocess.run(["protoc", "--python_out=.", "v2ray.proto"], check=True)

def parse_geosite(filename):
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
            if d.type == v2ray_pb2.Domain.Full:
                db[tag].append(f"DOMAIN,{d.value}")
            elif d.type == v2ray_pb2.Domain.Domain:
                db[tag].append(f"DOMAIN-SUFFIX,{d.value}")
            elif d.type == v2ray_pb2.Domain.Plain:
                db[tag].append(f"DOMAIN-KEYWORD,{d.value}")
            elif d.type == v2ray_pb2.Domain.Regex:
                continue
    return db

def parse_geoip(filename):
    import v2ray_pb2
    with open(filename, "rb") as f:
        data = f.read()

    geo_ip_list = v2ray_pb2.GeoIPList()
    geo_ip_list.ParseFromString(data)

    db = {}
    for entry in geo_ip_list.entry:
        tag = entry.country_code.lower()
        db[tag] = []
        for cidr in entry.cidr:
            # Преобразуем массив байт обратно в читаемый IP
            ip_bytes = cidr.ip
            prefix = cidr.prefix
            
            try:
                if len(ip_bytes) == 4: # IPv4
                    ip_str = str(ipaddress.IPv4Address(ip_bytes))
                    db[tag].append(f"IP-CIDR,{ip_str}/{prefix}")
                elif len(ip_bytes) == 16: # IPv6
                    ip_str = str(ipaddress.IPv6Address(ip_bytes))
                    db[tag].append(f"IP-CIDR6,{ip_str}/{prefix}")
            except Exception as e:
                print(f"Ошибка конвертации IP: {e}")
                continue
    return db

def main():
    # 1. Подготовка
    generate_protobuf_classes()
    
    # 2. Обработка GEOSITE (Домены)
    download_file(GEOSITE_URL, "geosite.dat")
    print("Парсинг базы данных geosite.dat...")
    geosite_db = parse_geosite("geosite.dat")
    
    for output_file, categories in DOMAINS_CONFIG.items():
        print(f"--- Формирование {output_file} ---")
        written = set()
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for cat in categories:
                cat_l = cat.lower()
                if cat_l in geosite_db:
                    for rule in geosite_db[cat_l]:
                        if rule not in written:
                            outfile.write(f"{rule}\n")
                            written.add(rule)
        print(f"Создан {output_file} (правил: {len(written)})")
        
    os.remove("geosite.dat")

    # 3. Обработка GEOIP (IP-адреса)
    download_file(GEOIP_URL, "geoip.dat")
    print("Парсинг базы данных geoip.dat...")
    geoip_db = parse_geoip("geoip.dat")
    
    for output_file, categories in IPS_CONFIG.items():
        print(f"--- Формирование {output_file} ---")
        written = set()
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for cat in categories:
                cat_l = cat.lower()
                if cat_l in geoip_db:
                    for rule in geoip_db[cat_l]:
                        if rule not in written:
                            outfile.write(f"{rule}\n")
                            written.add(rule)
                else:
                    print(f"Предупреждение: Категория IP '{cat}' не найдена в geoip.dat")
        print(f"Создан {output_file} (правил: {len(written)})")
        
    os.remove("geoip.dat")

    # Очистка временных файлов protobuf
    for f in ["v2ray.proto", "v2ray_pb2.py"]:
        if os.path.exists(f):
            os.remove(f)
            
    print("Вся сборка успешно завершена!")

if __name__ == "__main__":
    main()
