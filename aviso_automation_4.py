#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aviso YouTube Tasks Automation Script - УЛУЧШЕННАЯ ВЕРСИЯ
НОВЫЕ ФУНКЦИИ:
- Реорганизация в отдельные классы для каждого типа заданий
- Обработка антибот защиты YouTube
- Исправление ошибок и оптимизация скорости
- Уменьшение времени чтения и оптимизация прокрутки
"""

import os
import sys
import time
import random
import json
import logging
import subprocess
import platform
import re
import pickle
import hashlib
import shutil
import zipfile
import stat
import socket
import urllib3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import math

# Попытка импорта необходимых библиотек с автоустановкой
def install_requirements():
    """Автоматическая установка необходимых зависимостей"""
    required_packages = [
        'selenium',
        'requests',
        'beautifulsoup4',
        'fake-useragent',
        'webdriver-manager',
        'g4f'  # Добавляем g4f для GPT-4
    ]
    
    logging.info("📦 Проверка и установка зависимостей...")
    
    for package in required_packages:
        try:
            package_name = package.split('[')[0].replace('-', '_')
            __import__(package_name)
            logging.info(f"✓ Пакет {package} уже установлен")
        except ImportError:
            logging.info(f"⚠ Устанавливаю пакет {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logging.info(f"✓ Пакет {package} успешно установлен")
            except subprocess.CalledProcessError as e:
                logging.error(f"✗ Ошибка установки пакета {package}: {e}")
                try:
                    logging.info(f"🔄 Попытка альтернативной установки {package}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logging.info(f"✓ Пакет {package} установлен через --user")
                except subprocess.CalledProcessError:
                    logging.warning(f"⚠ Не удалось установить {package}, но продолжаем...")

# Настройка базового логирования до установки зависимостей
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Установка зависимостей
install_requirements()

# Импорт после установки
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.common.keys import Keys
    
    # ИСПРАВЛЕННЫЙ импорт исключений - совместимость с разными версиями Selenium
    try:
        from selenium.common.exceptions import (
            NoSuchElementException, 
            TimeoutException, 
            ElementClickInterceptedException,
            ElementNotInteractableError,
            WebDriverException
        )
    except ImportError:
        # Для старых версий Selenium
        from selenium.common.exceptions import (
            NoSuchElementException, 
            TimeoutException, 
            ElementClickInterceptedException,
            WebDriverException
        )
        # Создаем алиас для совместимости
        ElementNotInteractableError = WebDriverException
    
    try:
        from webdriver_manager.firefox import GeckoDriverManager as WDMGeckoDriverManager
    except ImportError:
        WDMGeckoDriverManager = None
    import requests
    from bs4 import BeautifulSoup
    from fake_useragent import UserAgent
    import g4f
except ImportError as e:
    logging.error(f"❌ Критическая ошибка импорта: {e}")
    logging.error("📋 Попробуйте установить зависимости вручую:")
    logging.error("pip install selenium requests beautifulsoup4 fake-useragent webdriver-manager g4f")
    sys.exit(1)

# Tor process management functions removed - no longer needed

class GeckoDriverManager:
    """Класс для управления geckodriver"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_termux = self.detect_termux()
        self.driver_path = None
        
    def detect_termux(self) -> bool:
        """Определение запуска в Termux"""
        return 'com.termux' in os.environ.get('PREFIX', '') or \
               '/data/data/com.termux' in os.environ.get('HOME', '')
    
    def get_latest_geckodriver_version(self) -> str:
        """Получение последней версии geckodriver"""
        try:
            response = requests.get('https://api.github.com/repos/mozilla/geckodriver/releases/latest', timeout=10)
            response.raise_for_status()
            data = response.json()
            return data['tag_name'].lstrip('v')
        except Exception as e:
            logging.warning(f"⚠ Не удалось получить версию geckodriver: {e}")
            return "0.33.0"  # Фоллбэк версия
    
    def download_geckodriver(self, version: str) -> Optional[str]:
        """Скачивание geckodriver"""
        try:
            # Определяем архитектуру и платформу
            if self.is_termux:
                platform_name = "linux-aarch64"
                if "aarch64" not in platform.machine():
                    platform_name = "linux32"
            elif self.system == 'linux':
                arch = platform.machine()
                if arch == 'x86_64':
                    platform_name = "linux64"
                elif arch == 'aarch64':
                    platform_name = "linux-aarch64"
                else:
                    platform_name = "linux32"
            elif self.system == 'windows':
                arch = platform.machine()
                if arch == 'AMD64':
                    platform_name = "win64"
                else:
                    platform_name = "win32"
            elif self.system == 'darwin':
                arch = platform.machine()
                if arch == 'arm64':
                    platform_name = "macos-aarch64"
                else:
                    platform_name = "macos"
            else:
                logging.error(f"✗ Неподдерживаемая платформа: {self.system}")
                return None
            
            # URL для скачивания
            if self.system == 'windows':
                filename = f"geckodriver-v{version}-{platform_name}.zip"
                executable_name = "geckodriver.exe"
            else:
                filename = f"geckodriver-v{version}-{platform_name}.tar.gz"
                executable_name = "geckodriver"
            
            url = f"https://github.com/mozilla/geckodriver/releases/download/v{version}/{filename}"
            
            logging.info(f"📥 Скачивание geckodriver v{version} для {platform_name}...")
            
            # Создаем директорию для драйверов
            drivers_dir = os.path.join(os.path.expanduser("~"), ".webdrivers")
            os.makedirs(drivers_dir, exist_ok=True)
            
            # Скачиваем файл
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            archive_path = os.path.join(drivers_dir, filename)
            with open(archive_path, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"✓ Geckodriver скачан: {archive_path}")
            
            # Извлекаем архив
            extract_dir = os.path.join(drivers_dir, f"geckodriver-{version}")
            os.makedirs(extract_dir, exist_ok=True)
            
            if filename.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                import tarfile
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            
            # Находим исполняемый файл
            driver_path = os.path.join(extract_dir, executable_name)
            
            if not os.path.exists(driver_path):
                # Ищем в подпапках
                for root, dirs, files in os.walk(extract_dir):
                    if executable_name in files:
                        driver_path = os.path.join(root, executable_name)
                        break
            
            if os.path.exists(driver_path):
                # Делаем исполняемым на Unix системах
                if self.system != 'windows':
                    st = os.stat(driver_path)
                    os.chmod(driver_path, st.st_mode | stat.S_IEXEC)
                
                logging.info(f"✅ Geckodriver установлен: {driver_path}")
                
                # Удаляем архив
                try:
                    os.remove(archive_path)
                except:
                    pass
                
                return driver_path
            else:
                logging.error(f"✗ Не найден исполняемый файл geckodriver в {extract_dir}")
                return None
                
        except Exception as e:
            logging.error(f"✗ Ошибка скачивания geckodriver: {e}")
            return None
    
    def find_geckodriver(self) -> Optional[str]:
        """Поиск geckodriver в системе"""
        # Проверяем в PATH
        try:
            if self.system == 'windows':
                result = subprocess.run(['where', 'geckodriver'], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', 'geckodriver'], capture_output=True, text=True)
            
            if result.returncode == 0:
                driver_path = result.stdout.strip()
                if os.path.exists(driver_path):
                    logging.info(f"✓ Найден geckodriver в PATH: {driver_path}")
                    return driver_path
        except:
            pass
        
        # Проверяем в стандартных местах
        possible_paths = []
        
        if self.is_termux:
            possible_paths = [
                '/data/data/com.termux/files/usr/bin/geckodriver',
                f"{os.environ.get('PREFIX', '')}/bin/geckodriver"
            ]
        elif self.system == 'linux':
            possible_paths = [
                '/usr/bin/geckodriver',
                '/usr/local/bin/geckodriver',
                '/opt/geckodriver/geckodriver',
                '/snap/bin/geckodriver'
            ]
        elif self.system == 'windows':
            possible_paths = [
                r"C:\Program Files\geckodriver\geckodriver.exe",
                r"C:\Program Files (x86)\geckodriver\geckodriver.exe",
                r"C:\geckodriver\geckodriver.exe"
            ]
        elif self.system == 'darwin':
            possible_paths = [
                '/usr/local/bin/geckodriver',
                '/opt/homebrew/bin/geckodriver'
            ]
        
        # Проверяем в домашней директории
        home_drivers = os.path.join(os.path.expanduser("~"), ".webdrivers")
        if os.path.exists(home_drivers):
            for root, dirs, files in os.walk(home_drivers):
                for file in files:
                    if file.startswith('geckodriver'):
                        possible_paths.append(os.path.join(root, file))
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                logging.info(f"✓ Найден geckodriver: {path}")
                return path
        
        return None
    
    def get_driver_path(self) -> str:
        """Получение пути к geckodriver с автоматической установкой"""
        if self.driver_path:
            return self.driver_path
        
        # Сначала ищем существующий
        driver_path = self.find_geckodriver()
        
        if not driver_path:
            logging.info("📦 Geckodriver не найден, начинаю автоматическую установку...")
            
            # Пробуем использовать webdriver-manager
            if WDMGeckoDriverManager:
                try:
                    logging.info("🔄 Попытка использования webdriver-manager...")
                    driver_path = WDMGeckoDriverManager().install()
                    if driver_path and os.path.exists(driver_path):
                        logging.info(f"✅ Geckodriver установлен через webdriver-manager: {driver_path}")
                        self.driver_path = driver_path
                        return driver_path
                except Exception as e:
                    logging.warning(f"⚠ Webdriver-manager не удался: {e}")
            
            # Скачиваем вручную
            version = self.get_latest_geckodriver_version()
            driver_path = self.download_geckodriver(version)
            
            if not driver_path:
                raise Exception("Не удалось установить geckodriver автоматически")
        
        self.driver_path = driver_path
        return driver_path

class UserAgentManager:
    """Класс для управления User-Agent для каждого аккаунта - СЛУЧАЙНЫЕ АГЕНТЫ"""
    
    def __init__(self):
        self.ua_file = "user_agents.json"
        self.user_agents = self.load_user_agents()
        
    def load_user_agents(self) -> Dict[str, str]:
        """Загрузка сохраненных User-Agent'ов"""
        try:
            if os.path.exists(self.ua_file):
                with open(self.ua_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.debug(f"⚠ Ошибка загрузки User-Agent'ов: {e}")
        
        return {}
    
    def save_user_agents(self):
        """Сохранение User-Agent'ов"""
        try:
            with open(self.ua_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_agents, f, indent=2, ensure_ascii=False)
            logging.debug("💾 User-Agent'ы сохранены")
        except Exception as e:
            logging.error(f"✗ Ошибка сохранения User-Agent'ов: {e}")
    
    def generate_random_user_agent(self) -> str:
        """Генерация полностью случайного User-Agent"""
        try:
            from fake_useragent import UserAgent
            ua = UserAgent()
            
            # Выбираем случайный тип браузера
            browser_types = ['chrome', 'firefox', 'safari', 'edge', 'opera']
            browser = random.choice(browser_types)
            
            # Генерируем User-Agent для выбранного браузера
            if browser == 'chrome':
                user_agent = ua.chrome
            elif browser == 'firefox':
                user_agent = ua.firefox
            elif browser == 'safari':
                user_agent = ua.safari
            elif browser == 'edge':
                user_agent = ua.edge
            elif browser == 'opera':
                user_agent = ua.opera
            else:
                user_agent = ua.random
            
            return user_agent
            
        except Exception as e:
            logging.warning(f"⚠ Ошибка генерации User-Agent: {e}")
            # Fallback - возвращаем случайный из предустановленных
            fallback_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
            ]
            return random.choice(fallback_agents)
    
    def get_user_agent(self, username: str) -> str:
        """Получение User-Agent для конкретного пользователя - СЛУЧАЙНЫЙ"""
        # Создаем уникальный ключ для пользователя
        user_key = hashlib.md5(username.encode()).hexdigest()
        
        if user_key not in self.user_agents:
            # Генерируем полностью случайный User-Agent
            random_ua = self.generate_random_user_agent()
            
            self.user_agents[user_key] = random_ua
            self.save_user_agents()
            logging.info(f"🎭 Создан новый случайный User-Agent для пользователя {username}")
        
        user_agent = self.user_agents[user_key]
        logging.info(f"🎭 Используется User-Agent для {username}: {user_agent[:80]}...")
        return user_agent

class HumanBehaviorSimulator:
    """Класс для имитации человеческого поведения"""
    
    @staticmethod
    def random_sleep(min_seconds: float = 0.1, max_seconds: float = 0.5):
        """Случайная пауза - УМЕНЬШЕНЫ ЗАДЕРЖКИ"""
        sleep_time = random.uniform(min_seconds, max_seconds)
        logging.debug(f"💤 Пауза {sleep_time:.2f} секунд")
        time.sleep(sleep_time)
    
    @staticmethod
    def generate_bezier_curve(start: Tuple[int, int], end: Tuple[int, int], 
                            control_points: int = 2) -> List[Tuple[int, int]]:
        """Генерация кривой Безье для движения мыши - УСКОРЕНО"""
        def bezier_point(t: float, points: List[Tuple[int, int]]) -> Tuple[int, int]:
            n = len(points) - 1
            x = sum(math.comb(n, i) * (1-t)**(n-i) * t**i * points[i][0] for i in range(n+1))
            y = sum(math.comb(n, i) * (1-t)**(n-i) * t**i * points[i][1] for i in range(n+1))
            return int(x), int(y)
        
        # Создаем контрольные точки
        control_pts = [start]
        for _ in range(control_points):
            x = random.randint(min(start[0], end[0]), max(start[0], end[0]))
            y = random.randint(min(start[1], end[1]), max(start[1], end[1]))
            control_pts.append((x, y))
        control_pts.append(end)
        
        # Генерируем точки кривой - УМЕНЬШЕНО количество точек
        curve_points = []
        steps = random.randint(5, 15)  # Уменьшено с 10-30
        for i in range(steps + 1):
            t = i / steps
            point = bezier_point(t, control_pts)
            curve_points.append(point)
        
        return curve_points
    
    @staticmethod
    def human_like_typing(element, text: str, driver):
        """УСКОРЕННАЯ имитация человеческого набора текста"""
        element.clear()
        HumanBehaviorSimulator.random_sleep(0.1, 2) 
        
        # Раскладки клавиатуры для имитации опечаток
        qwerty_neighbors = {
            'q': ['w', 'a'], 'w': ['q', 'e', 's'], 'e': ['w', 'r', 'd'], 'r': ['e', 't', 'f'],
            't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'], 'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'],
            'o': ['i', 'p', 'l'], 'p': ['o', 'l'], 'a': ['q', 's', 'z'], 's': ['w', 'a', 'd', 'x'],
            'd': ['e', 's', 'f', 'c'], 'f': ['r', 'd', 'g', 'v'], 'g': ['t', 'f', 'h', 'b'],
            'h': ['y', 'g', 'j', 'n'], 'j': ['u', 'h', 'k', 'm'], 'k': ['i', 'j', 'l'],
            'l': ['o', 'k', 'p'], 'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'],
            'c': ['x', 'd', 'f', 'v'], 'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'],
            'n': ['b', 'h', 'j', 'm'], 'm': ['n', 'j', 'k'],
            '1': ['2', 'q'], '2': ['1', '3', 'q', 'w'], '3': ['2', '4', 'w', 'e'],
            '4': ['3', '5', 'e', 'r'], '5': ['4', '6', 'r', 't'], '6': ['5', '7', 't', 'y'],
            '7': ['6', '8', 'y', 'u'], '8': ['7', '9', 'u', 'i'], '9': ['8', '0', 'i', 'o'],
            '0': ['9', 'o', 'p']
        }
        
        typed_text = ""
        i = 0
        
        while i < len(text):
            char = text[i].lower()
            
            # Случайные паузы между символами - БЫСТРЕЕ
            if char == ' ':
                pause = random.uniform(0.02, 1)  # Уменьшено
            elif char.isdigit():
                pause = random.uniform(0.01, 1)  # Уменьшено
            else:
                pause = random.uniform(0.01, 1)  # Уменьшено
            
            time.sleep(pause)
            
            # Имитация опечаток (2% вероятность - уменьшено)
            if random.random() < 0.02 and char in qwerty_neighbors:
                # Делаем опечатку
                wrong_char = random.choice(qwerty_neighbors[char])
                element.send_keys(wrong_char)
                typed_text += wrong_char
                logging.debug(f"🔤 Опечатка: '{wrong_char}' вместо '{char}'")
                
                # Пауза перед исправлением - БЫСТРЕЕ
                time.sleep(random.uniform(0.05, 0.15))
                
                # Исправляем опечатку
                element.send_keys(Keys.BACKSPACE)
                typed_text = typed_text[:-1]
                time.sleep(random.uniform(0.02, 0.08))
                
                # Печатаем правильный символ
                element.send_keys(text[i])
                typed_text += text[i]
                logging.debug(f"🔤 Исправлено на: '{text[i]}'")
                
            # Имитация двойного нажатия (0.5% вероятность - уменьшено)
            elif random.random() < 0.005:
                element.send_keys(text[i])
                element.send_keys(text[i])  # Двойное нажатие
                typed_text += text[i] + text[i]
                logging.debug(f"🔤 Двойное нажатие: '{text[i]}'")
                
                # Пауза и исправление
                time.sleep(random.uniform(0.05, 0.15))
                element.send_keys(Keys.BACKSPACE)
                typed_text = typed_text[:-1]
                
            else:
                # Обычное нажатие
                element.send_keys(text[i])
                typed_text += text[i]
            
            # Случайные более длинные паузы - РЕЖЕ
            if random.random() < 0.01:  # 1% вероятность
                thinking_pause = random.uniform(0.1, 0.4)  # Уменьшено
                logging.debug(f"🤔 Пауза для размышления: {thinking_pause:.2f}с")
                time.sleep(thinking_pause)
            
            i += 1
        
        # Финальная пауза после ввода - БЫСТРЕЕ
        HumanBehaviorSimulator.random_sleep(0.1, 0.25)
    
    @staticmethod
    def calculate_reading_time(text: str) -> float:
        """БЫСТРЕЕ - расчет времени чтения текста (в 2 раза быстрее)"""
        # Подсчет слов
        words = len(text.split())
        
        # Подсчет символов
        chars = len(text)
        
        # УВЕЛИЧЕННАЯ скорость чтения: 300 слов в минуту или 5 слов в секунду (было 3.7)
        words_per_second = 5.0
        
        # Время чтения по словам
        reading_time_by_words = words / words_per_second
        
        # Дополнительное время для сложных символов (уменьшено)
        complex_chars = sum(1 for c in text if not c.isalpha() and not c.isspace())
        additional_time = complex_chars * 0.05  # Уменьшено с 0.1
        
        # Минимальное время чтения (уменьшено)
        min_time = max(2, words * 0.1)  # Уменьшено с 5 и 0.2
        
        total_time = max(min_time, reading_time_by_words + additional_time)
        
        # Добавляем случайность ±30%
        variation = random.uniform(0.7, 1.3)
        final_time = total_time * variation
        
        # В 2 раза быстрее
        final_time = final_time / 2
        
        logging.info(f"📚 Время чтения {words} слов (~{chars} символов): {final_time:.1f} секунд")
        return final_time

class GPTManager:
    """Менеджер для работы с GPT через g4f"""
    
    def __init__(self):
        try:
            import g4f
            self.g4f = g4f
            logging.info("✅ g4f инициализирован")
        except ImportError:
            logging.error("❌ g4f не установлен")
            self.g4f = None
    
    def ask_gpt(self, letter_text: str, question: str, answers: List[str]) -> Optional[str]:
        """ИСПРАВЛЕННЫЙ запрос к GPT через g4f"""
        if not self.g4f:
            logging.error("❌ g4f не доступен")
            return None
        
        try:
            # Формируем промпт для GPT
            prompt = f"""Твоя задача: прочитать текст и выбрать верный ответ вопрос основываясь на самом тексте. Ответь исключительно номером верного ответа из доступных. Не пиши совершенно ничего кроме номера ответа цифрой. 

Текст: {letter_text}

Вопрос: {question}

Варианты ответов:"""
            for i, answer in enumerate(answers, 1):
                prompt += f"{i}. {answer}\n"
            
            prompt += "\nВыбери номер правильного ответа (только цифру):"
            
            # ИСПРАВЛЕНИЕ: Правильное использование g4f
            response = self.g4f.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Ты помощник для ответов на вопросы по тексту. Отвечай только номером правильного ответа."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # ИСПРАВЛЕНИЕ: Правильное извлечение ответа из g4f
            if response and 'choices' in response and len(response['choices']) > 0:
                gpt_answer = response['choices'][0]['message']['content'].strip()
            elif isinstance(response, str):
                gpt_answer = response.strip()
            else:
                logging.error("❌ Неожиданный формат ответа от g4f")
                return None
            
            # Проверяем что ответ - это число от 1 до количества вариантов
            if gpt_answer.isdigit() and 1 <= int(gpt_answer) <= len(answers):
                logging.info(f"🤖 GPT выбрал ответ: {gpt_answer}")
                return gpt_answer
            else:
                logging.error(f"❌ Некорректный ответ от GPT: {gpt_answer}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Ошибка GPT: {e}")
            return None

# SimpleTorManager class removed - browser now works without Tor proxy

class TaskCoordinator:
    """Класс для координации выполнения разных типов заданий"""
    
    def __init__(self):
        self.task_types = ['surf', 'letters']  # Removed 'youtube'
        self.current_cycle_tasks = []
        self.reset_cycle()
    
    def reset_cycle(self):
        """Сброс цикла заданий"""
        self.current_cycle_tasks = self.task_types.copy()
        random.shuffle(self.current_cycle_tasks)
        logging.info(f"🔄 Новый цикл заданий: {' → '.join(self.current_cycle_tasks)}")
    
    def get_next_task_type(self) -> Optional[str]:
        """Получение следующего типа заданий абсолютно случайно"""
        if not self.current_cycle_tasks:
            self.reset_cycle()
        task_type = random.choice(self.current_cycle_tasks)
        self.current_cycle_tasks.remove(task_type)
        logging.info(f"🎯 Текущий тип заданий (случайный выбор): {task_type}")
        return task_type
    
    def is_cycle_complete(self) -> bool:
        """Проверка завершения цикла"""
        return len(self.current_cycle_tasks) == 0

# YouTubeTaskHandler class removed - YouTube functionality disabled
class SurfTaskHandler:
    """Класс для обработки заданий на серфинг"""
    
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        self.failed_task_ids = set()  # Отслеживание заданий с ошибками
        self.error_tasks = set()  # Отслеживание заданий с ошибками заявок
    
    def get_tasks(self) -> List[Dict]:
        """Получение заданий на серфинг с проверкой реального существования элементов"""
        logging.info("🌊 Поиск заданий на серфинг...")
        
        try:
            if "/tasks-surf" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/tasks-surf")
                time.sleep(1)
            
            # ИСПРАВЛЕННЫЙ JavaScript с проверкой существования элементов
            surf_tasks_data = self.driver.execute_script("""
                var tasks = [];
                var totalEarnings = 0;
                var errorTasks = [];
                var rows = document.querySelectorAll("tr[class^='de_']");
                
                for (var i = 0; i < rows.length; i++) {
                    try {
                        var row = rows[i];
                        var className = row.className;
                        var taskIdMatch = className.match(/de_(\\d+)/);
                        
                        if (taskIdMatch) {
                            var taskId = taskIdMatch[1];
                            var startDiv = row.querySelector("div[id='start-serf-" + taskId + "']");
                            
                            // КРИТИЧЕСКАЯ ПРОВЕРКА: элемент должен быть видим и существовать
                            if (!startDiv || startDiv.offsetParent === null) {
                                continue; // Пропускаем невидимые элементы
                            }
                            
                            // Проверяем наличие ошибки заявки
                            var errorElement = row.querySelector('.start-error-serf');
                            if (errorElement && errorElement.offsetParent !== null) {
                                errorTasks.push(taskId);
                                continue; // Пропускаем задания с ошибкой
                            }
                            
                            var link = startDiv.querySelector("a");
                            
                            // КРИТИЧЕСКАЯ ПРОВЕРКА: ссылка должна существовать и быть видимой
                            if (!link || link.offsetParent === null) {
                                continue; // Пропускаем если ссылка не видна
                            }
                            
                            // ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: ссылка должна быть кликабельной
                            var linkRect = link.getBoundingClientRect();
                            if (linkRect.width === 0 || linkRect.height === 0) {
                                continue; // Пропускаем элементы с нулевым размером
                            }
                            
                            var title = link.textContent.trim();
                            var url = link.getAttribute('title') || link.getAttribute('href') || 'unknown';
                            
                            // Парсим стоимость просмотра
                            var priceElement = row.querySelector('td[style*="text-align:right"] span[title="Стоимость просмотра"]');
                            var price = 0;
                            if (priceElement) {
                                var priceText = priceElement.textContent.trim();
                                var priceMatch = priceText.match(/([0-9.,]+)/);
                                if (priceMatch) {
                                    price = parseFloat(priceMatch[1].replace(',', '.'));
                                    totalEarnings += price;
                                }
                            }
                            
                            tasks.push({
                                id: taskId,
                                title: title,
                                url: url,
                                price: price,
                                row_class: className,
                                start_div_id: "start-serf-" + taskId
                            });
                        }
                    } catch (e) {
                        // Пропускаем ошибочные элементы
                        console.log('Ошибка обработки элемента:', e);
                    }
                }
                
                return {
                    tasks: tasks,
                    totalEarnings: totalEarnings,
                    errorTasks: errorTasks
                };
            """)
            
            tasks = []
            total_earnings = surf_tasks_data.get('totalEarnings', 0)
            error_tasks = surf_tasks_data.get('errorTasks', [])
            
            # Обновляем список заданий с ошибками
            self.error_tasks.update(error_tasks)
            
            for task_data in surf_tasks_data.get('tasks', []):
                try:
                    task_id = task_data['id']
                    
                    # Пропускаем задания, которые уже имели ошибки
                    if task_id in self.failed_task_ids:
                        logging.info(f"⚠ Пропускаем задание {task_id} - уже было с ошибкой")
                        continue
                    
                    # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА СУЩЕСТВОВАНИЯ через Selenium
                    try:
                        element_check = self.driver.find_element(By.ID, task_data['start_div_id'])
                        link_check = element_check.find_element(By.TAG_NAME, "a")
                        
                        # Проверяем что элемент видим
                        if not element_check.is_displayed() or not link_check.is_displayed():
                            logging.warning(f"⚠ Задание {task_id} найдено в DOM но не отображается, пропускаем")
                            continue
                            
                    except NoSuchElementException:
                        logging.warning(f"⚠ Элементы задания {task_id} не найдены в DOM, пропускаем")
                        continue
                    except Exception as e:
                        logging.warning(f"⚠ Ошибка проверки элементов задания {task_id}: {e}")
                        continue
                    
                    task_info = {
                        'id': task_id,
                        'title': task_data['title'],
                        'url': task_data['url'],
                        'price': task_data['price'],
                        'row_class': task_data['row_class'],
                        'start_div_id': task_data['start_div_id']
                    }
                    tasks.append(task_info)
                    
                except Exception as e:
                    logging.debug(f"⚠ Ошибка создания задания серфинга: {e}")
                    continue
            
            # Информация о найденных заданиях
            logging.info(f"🌊 Найдено РЕАЛЬНО СУЩЕСТВУЮЩИХ серфинг заданий: {len(tasks)}")
            if error_tasks:
                logging.info(f"⚠ Заданий с ошибками заявок: {len(error_tasks)}")
            if self.failed_task_ids:
                logging.info(f"⚠ Заданий с предыдущими ошибками: {len(self.failed_task_ids)}")
            logging.info(f"💰 Общий заработок за серфинг: {total_earnings:.4f} руб.")
            
            return tasks
            
        except Exception as e:
            logging.error(f"❌ Ошибка получения серфинг заданий: {e}")
            return []
    
    def execute_task(self, task: Dict) -> bool:
        """Выполнение задания на серфинг с улучшенной обработкой прокрутки и кликов"""
        task_id = task['id']
        logging.info(f"🌊 Серфинг задание {task_id}: {task['title'][:50]}...")
        
        original_window = self.driver.current_window_handle
        
        try:
            if "/tasks-surf" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/tasks-surf")
                time.sleep(1)
            
            try:
                task_row = self.driver.find_element(By.CSS_SELECTOR, f"tr.{task['row_class']}")
                start_div = self.driver.find_element(By.ID, task['start_div_id'])
                start_link = start_div.find_element(By.TAG_NAME, "a")
            except NoSuchElementException:
                logging.warning(f"⚠ Элементы серфинг задания {task_id} не найдены")
                return False
            except Exception as e:
                logging.error(f"❌ Ошибка поиска элементов серфинг задания {task_id}: {e}")
                return False
            
            # УЛУЧШЕННАЯ прокрутка и обработка кликов
            try:
                # Метод 1: Плавная прокрутка к элементу
                logging.info(f"🔄 Прокрутка к элементу задания {task_id}")
                self.driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth', 
                        block: 'center', 
                        inline: 'center'
                    });
                """, start_link)
                time.sleep(1)  # Даем больше времени на прокрутку
                
                # Проверяем видимость элемента
                is_visible = self.driver.execute_script("""
                    var elem = arguments[0];
                    var rect = elem.getBoundingClientRect();
                    var windowHeight = window.innerHeight || document.documentElement.clientHeight;
                    var windowWidth = window.innerWidth || document.documentElement.clientWidth;
                    
                    return (
                        rect.top >= 0 &&
                        rect.left >= 0 &&
                        rect.bottom <= windowHeight &&
                        rect.right <= windowWidth &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                """, start_link)
                
                if not is_visible:
                    logging.warning(f"⚠ Элемент {task_id} не в видимой области после прокрутки")
                    
                    # Метод 2: Принудительная прокрутка через JavaScript
                    logging.info(f"🔄 Принудительная прокрутка к элементу {task_id}")
                    self.driver.execute_script("""
                        var elem = arguments[0];
                        var rect = elem.getBoundingClientRect();
                        var absoluteElementTop = rect.top + window.pageYOffset;
                        var middle = absoluteElementTop - (window.innerHeight / 2);
                        window.scrollTo(0, middle);
                    """, start_link)
                    time.sleep(1)
                    
                    # Повторная проверка видимости
                    is_visible = self.driver.execute_script("""
                        var elem = arguments[0];
                        var rect = elem.getBoundingClientRect();
                        var windowHeight = window.innerHeight || document.documentElement.clientHeight;
                        var windowWidth = window.innerWidth || document.documentElement.clientWidth;
                        
                        return (
                            rect.top >= 0 &&
                            rect.left >= 0 &&
                            rect.bottom <= windowHeight &&
                            rect.right <= windowWidth &&
                            rect.width > 0 &&
                            rect.height > 0
                        );
                    """, start_link)
                    
                    if not is_visible:
                        logging.warning(f"⚠ Элемент {task_id} все еще не в видимой области")
                        
                        # Метод 3: Увеличиваем размер окна если возможно
                        try:
                            current_size = self.driver.get_window_size()
                            if current_size['height'] < 1000:
                                self.driver.set_window_size(current_size['width'], min(1200, current_size['height'] + 300))
                                logging.info(f"🔄 Увеличен размер окна для задания {task_id}")
                                time.sleep(0.5)
                        except:
                            pass
                        
                        # Метод 4: Прокрутка к началу страницы и затем к элементу
                        self.driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_link)
                        time.sleep(1)
                
                # Проверяем что элемент кликабелен
                is_clickable = self.driver.execute_script("""
                    var elem = arguments[0];
                    var rect = elem.getBoundingClientRect();
                    
                    // Проверяем что элемент не перекрыт другими элементами
                    var topElement = document.elementFromPoint(
                        rect.left + rect.width/2, 
                        rect.top + rect.height/2
                    );
                    
                    return topElement === elem || elem.contains(topElement);
                """, start_link)
                
                if not is_clickable:
                    logging.warning(f"⚠ Элемент {task_id} перекрыт другими элементами")
                    
                    # Пытаемся удалить перекрывающие элементы
                    self.driver.execute_script("""
                        var elem = arguments[0];
                        var rect = elem.getBoundingClientRect();
                        var centerX = rect.left + rect.width/2;
                        var centerY = rect.top + rect.height/2;
                        
                        // Находим элемент в центре нашего элемента
                        var topElement = document.elementFromPoint(centerX, centerY);
                        
                        // Если это не наш элемент, пытаемся его скрыть
                        if (topElement && topElement !== elem && !elem.contains(topElement)) {
                            var style = topElement.style;
                            style.display = 'none';
                            style.visibility = 'hidden';
                            style.zIndex = '-1';
                        }
                    """, start_link)
                    time.sleep(0.5)
                
                # Наведение мыши на элемент
                try:
                    ActionChains(self.driver).move_to_element(start_link).perform()
                    time.sleep(0.5)
                except Exception as e:
                    logging.debug(f"⚠ Ошибка наведения мыши на элемент {task_id}: {e}")
                
            except Exception as e:
                logging.error(f"❌ Ошибка подготовки элемента {task_id}: {e}")
            
            time.sleep(random.uniform(0.1, 0.5))
            
            # СЛУЧАЙНАЯ ЗАДЕРЖКА перед кликом
            pause = random.uniform(1, 5)
            logging.info(f"⏳ Случайная пауза перед кликом {pause:.1f}с")
            time.sleep(pause)
            
            # УЛУЧШЕННЫЙ клик с несколькими попытками
            click_success = False
            click_attempts = 0
            max_click_attempts = 5
            
            while not click_success and click_attempts < max_click_attempts:
                click_attempts += 1
                
                try:
                    logging.info(f"🖱 Попытка клика {click_attempts}/{max_click_attempts} по заданию {task_id}")
                    
                    # Метод 1: Обычный клик
                    if click_attempts == 1:
                        start_link.click()
                        
                    # Метод 2: Клик через ActionChains
                    elif click_attempts == 2:
                        ActionChains(self.driver).click(start_link).perform()
                        
                    # Метод 3: JavaScript клик
                    elif click_attempts == 3:
                        self.driver.execute_script("arguments[0].click();", start_link)
                        
                    # Метод 4: Клик по координатам
                    elif click_attempts == 4:
                        location = start_link.location
                        size = start_link.size
                        x = location['x'] + size['width'] // 2
                        y = location['y'] + size['height'] // 2
                        ActionChains(self.driver).move_by_offset(x, y).click().perform()
                        
                    # Метод 5: Принудительный JavaScript клик с событиями
                    elif click_attempts == 5:
                        self.driver.execute_script("""
                            var elem = arguments[0];
                            var event = new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true
                            });
                            elem.dispatchEvent(event);
                        """, start_link)
                    
                    logging.info(f"✅ Клик по заданию {task_id} выполнен (метод {click_attempts})")
                    click_success = True
                    
                except ElementClickInterceptedException as e:
                    logging.warning(f"⚠ Элемент {task_id} перехвачен при клике (попытка {click_attempts}): {e}")
                    time.sleep(0.5)
                    
                except ElementNotInteractableError as e:
                    logging.warning(f"⚠ Элемент {task_id} не интерактивен (попытка {click_attempts}): {e}")
                    time.sleep(0.5)
                    
                except Exception as e:
                    logging.warning(f"⚠ Ошибка клика по заданию {task_id} (попытка {click_attempts}): {e}")
                    time.sleep(0.5)
            
            if not click_success:
                logging.error(f"❌ Не удалось кликнуть по заданию {task_id} после {max_click_attempts} попыток")
                return False
            
            time.sleep(2)
            
            # ИСПРАВЛЕННАЯ проверка ошибки: только для конкретного задания
            if self.check_task_error_for_current_task(task_id):
                logging.warning(f"⚠ Ошибка заявки для задания {task_id}, переходим к следующему")
                self.failed_task_ids.add(task_id)
                self.error_tasks.add(task_id)
                return False
            
            wait = WebDriverWait(self.driver, 15)
            
            try:
                start_viewing_button = wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "start-yes-serf"))
                )
                
                # СЛУЧАЙНАЯ ЗАДЕРЖКА перед подтверждением
                confirm_pause = random.uniform(0.1, 2)
                logging.info(f"⏳ Случайная пауза перед подтверждением просмотра: {confirm_pause:.1f}с")
                time.sleep(confirm_pause)
                
                # Прокрутка к кнопке подтверждения
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", start_viewing_button)
                time.sleep(0.5)
                
                start_viewing_button.click()
                logging.info("✅ Нажата кнопка 'Приступить к просмотру'")
            except:
                # Повторная проверка ошибки если кнопка не найдена
                if self.check_task_error_for_current_task(task_id):
                    logging.warning(f"⚠ Ошибка заявки для задания {task_id} при ожидании кнопки")
                    self.failed_task_ids.add(task_id)
                    self.error_tasks.add(task_id)
                    return False
                
                logging.error("❌ Не найдена кнопка 'Приступить к просмотру'")
                return False
            
            time.sleep(5)
            
            # Переключение на новое окно
            all_windows = self.driver.window_handles
            new_window = None
            for window in all_windows:
                if window != original_window:
                    self.driver.switch_to.window(window)
                    new_window = window
                    break
            
            if not new_window:
                logging.error("❌ Новое окно серфинга не найдено")
                return False
            
            logging.info("🚀 Начинаем поиск таймера/кнопки в новом окне...")
            
            # Правильный поиск таймера в frame на сайте
            if self.wait_for_surf_timer_completion():
                logging.info("✅ Серфинг задание завершено!")
                
                time.sleep(random.uniform(0.2, 1))
                
                try:
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                except:
                    try:
                        for window in self.driver.window_handles:
                            if window == original_window:
                                self.driver.switch_to.window(window)
                                break
                    except:
                        pass
                
                logging.info("🔄 Обновление страницы серфинга...")
                self.driver.refresh()
                time.sleep(2)
                
                return True
            else:
                logging.error(f"❌ Серфинг задание {task_id} не завершено")
                return False
                
        except Exception as e:
            logging.error(f"❌ Ошибка серфинг задания {task_id}: {e}")
            return False
        finally:
            try:
                current_windows = self.driver.window_handles
                if len(current_windows) > 1:
                    for window in current_windows:
                        if window != original_window:
                            try:
                                self.driver.switch_to.window(window)
                                self.driver.close()
                            except:
                                pass
                    
                    try:
                        self.driver.switch_to.window(original_window)
                    except:
                        available_windows = self.driver.window_handles
                        if available_windows:
                            self.driver.switch_to.window(available_windows[0])
            except Exception as cleanup_error:
                logging.debug(f"⚠ Ошибка очистки окон серфинга: {cleanup_error}")
    
    def check_task_error_for_current_task(self, task_id: str) -> bool:
        """ИСПРАВЛЕННАЯ проверка ошибки: только для конкретного задания"""
        try:
            # Ищем ошибку в контексте конкретного задания
            error_check_result = self.driver.execute_script("""
                var taskId = arguments[0];
                var result = {
                    has_error: false,
                    error_text: '',
                    task_specific_error: false
                };
                
                // Проверяем общие ошибки
                var generalErrors = document.querySelectorAll('.start-error-serf');
                for (var i = 0; i < generalErrors.length; i++) {
                    var errorElement = generalErrors[i];
                    if (errorElement.offsetParent !== null) {
                        result.has_error = true;
                        result.error_text = errorElement.textContent.trim();
                        
                        // Проверяем, связана ли ошибка с нашим заданием
                        var parentRow = errorElement.closest('tr');
                        if (parentRow) {
                            var taskDiv = parentRow.querySelector('#start-serf-' + taskId);
                            if (taskDiv) {
                                result.task_specific_error = true;
                                break;
                            }
                        }
                    }
                }
                
                return result;
            """, task_id)
            
            if error_check_result['task_specific_error']:
                logging.info(f"🚫 Найдена ошибка для задания {task_id}: {error_check_result['error_text']}")
                return True
            elif error_check_result['has_error']:
                logging.debug(f"ℹ Найдена общая ошибка (не для задания {task_id}): {error_check_result['error_text']}")
                return False
            else:
                return False
                
        except Exception as e:
            logging.debug(f"⚠ Ошибка проверки элемента ошибки для задания {task_id}: {e}")
            return False
    
    def check_all_tasks_failed(self, available_tasks: List[Dict]) -> bool:
        """Проверка что все задания завершились ошибкой"""
        if not available_tasks:
            return True
        
        available_task_ids = set(task['id'] for task in available_tasks)
        failed_count = len(self.failed_task_ids.intersection(available_task_ids))
        
        if failed_count == len(available_tasks):
            logging.info(f"⚠ Все {len(available_tasks)} серфинг заданий завершились ошибкой, считаем выполненными")
            return True
        
        return False
    
    def has_available_tasks(self) -> bool:
        """Проверка наличия доступных заданий (без ошибок)"""
        try:
            if "/tasks-surf" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/tasks-surf")
                time.sleep(1)
            
            # Получаем информацию о всех заданиях и их ошибках
            task_status = self.driver.execute_script("""
                var totalTasks = 0;
                var errorTasks = 0;
                var availableTasks = 0;
                var rows = document.querySelectorAll("tr[class^='de_']");
                
                for (var i = 0; i < rows.length; i++) {
                    try {
                        var row = rows[i];
                        var className = row.className;
                        var taskIdMatch = className.match(/de_(\\d+)/);
                        
                        if (taskIdMatch) {
                            var taskId = taskIdMatch[1];
                            var startDiv = row.querySelector("div[id='start-serf-" + taskId + "']");
                            
                            if (startDiv) {
                                totalTasks++;
                                
                                // Проверяем наличие ошибки заявки
                                var errorElement = row.querySelector('.start-error-serf');
                                if (errorElement && errorElement.offsetParent !== null) {
                                    errorTasks++;
                                } else {
                                    availableTasks++;
                                }
                            }
                        }
                    } catch (e) {
                        // Пропускаем ошибочные элементы
                    }
                }
                
                return {
                    totalTasks: totalTasks,
                    errorTasks: errorTasks,
                    availableTasks: availableTasks
                };
            """)
            
            total_tasks = task_status.get('totalTasks', 0)
            error_tasks = task_status.get('errorTasks', 0)
            available_tasks = task_status.get('availableTasks', 0)
            
            logging.info(f"📊 Статус серфинг заданий: всего={total_tasks}, ошибки={error_tasks}, доступно={available_tasks}")
            
            # Если все задания имеют ошибки и общее количество > 0
            if total_tasks > 0 and error_tasks == total_tasks:
                logging.info("🚫 Все серфинг задания имеют ошибки заявок, переходим к следующему типу")
                return False
            
            return available_tasks > 0
            
        except Exception as e:
            logging.error(f"❌ Ошибка проверки доступности заданий: {e}")
            return False
    
    def wait_for_surf_timer_completion(self) -> bool:
        """Ожидание таймера серфинга или кнопки подтверждения"""
        logging.info("⏱ Ожидание таймера серфинга или кнопки подтверждения...")
        
        try:
            max_wait_time = 150
            checks_count = 0
            
            logging.info("🔄 Ожидание загрузки страницы...")
            time.sleep(2)
            
            while checks_count < max_wait_time:
                checks_count += 1
                
                # Поиск в frame
                frame_result = self.search_in_frames_with_names()
                
                if frame_result['button_found']:
                    logging.info("✅ Найдена кнопка подтверждения в frame!")
                    return True
                
                if frame_result['timer_found']:
                    timer_value = frame_result.get('timer_value')
                    if timer_value is not None:
                        if checks_count % 5 == 0:
                            logging.info(f"⏰ Таймер серфинга (frame): {timer_value}с")
                        
                        if timer_value <= 0:
                            logging.info("✅ Таймер завершен")
                            return True
                
                if checks_count % 10 == 0:
                    logging.info("⏳ Поиск таймера или кнопки в frame...")
                
                time.sleep(1)
            
            logging.error("❌ Время ожидания истекло")
            return False
            
        except Exception as e:
            logging.error(f"❌ Ошибка ожидания таймера серфинга: {e}")
            return False
    
    def search_in_frames_with_names(self) -> Dict:
        """Поиск элементов в frame - РАБОЧАЯ ВЕРСИЯ"""
        result = {
            'timer_found': False,
            'timer_value': None,
            'captcha_found': False,
            'button_found': False,
            'iframe_switched': False
        }
        
        try:
            # Быстрое получение информации о frame
            frame_info = self.driver.execute_script("""
                var frames = [];
                var iframes = document.getElementsByTagName('iframe');
                var frameElements = document.getElementsByTagName('frame');
                
                for (var i = 0; i < iframes.length; i++) {
                    frames.push({
                        type: 'iframe',
                        index: i,
                        name: iframes[i].name || '',
                        src: iframes[i].src || '',
                        id: iframes[i].id || ''
                    });
                }
                
                for (var i = 0; i < frameElements.length; i++) {
                    frames.push({
                        type: 'frame',
                        index: i,
                        name: frameElements[i].name || '',
                        src: frameElements[i].src || '',
                        id: frameElements[i].id || ''
                    });
                }
                
                return frames;
            """)
            
            for frame in frame_info:
                try:
                    frame_type = frame['type']
                    frame_name = frame['name']
                    
                    # Быстрое переключение на frame
                    if frame_name:
                        try:
                            self.driver.switch_to.frame(frame_name)
                        except:
                            if frame_type == 'iframe':
                                iframe_element = self.driver.find_elements(By.TAG_NAME, "iframe")[frame['index']]
                                self.driver.switch_to.frame(iframe_element)
                            else:
                                frame_element = self.driver.find_elements(By.TAG_NAME, "frame")[frame['index']]
                                self.driver.switch_to.frame(frame_element)
                    else:
                        if frame_type == 'iframe':
                            iframe_element = self.driver.find_elements(By.TAG_NAME, "iframe")[frame['index']]
                            self.driver.switch_to.frame(iframe_element)
                        else:
                            frame_element = self.driver.find_elements(By.TAG_NAME, "frame")[frame['index']]
                            self.driver.switch_to.frame(frame_element)
                    
                    result['iframe_switched'] = True
                    
                    # Быстрый поиск элементов
                    frame_status = self.driver.execute_script("""
                        var result = {
                            timer_found: false,
                            timer_value: null,
                            button_found: false,
                            button_element: null
                        };
                        
                        // Поиск таймера
                        var timerSelectors = [
                            'span.timer.notranslate#timer_inp', 
                            'span#timer_inp', 
                            'span.timer',
                            'span#tmr',
                            '#tmr',
                            '.tmr'
                        ];
                        
                        for (var s = 0; s < timerSelectors.length; s++) {
                            try {
                                var elements = document.querySelectorAll(timerSelectors[s]);
                                for (var t = 0; t < elements.length; t++) {
                                    var element = elements[t];
                                    var elementText = element.textContent.trim();
                                    
                                    if (element.offsetParent !== null && /^\\d+$/.test(elementText)) {
                                        result.timer_found = true;
                                        result.timer_value = parseInt(elementText);
                                        break;
                                    }
                                }
                                if (result.timer_found) break;
                            } catch (e) {
                                // Пропускаем ошибки
                            }
                        }
                        
                        // Поиск кнопок
                        var buttonSelectors = [
                            'a.btn_capt', 
                            'a[href*="vlss?view=ok"]', 
                            'a[href*="view=ok"]',
                            'button[type="submit"]',
                            'input[type="submit"]'
                        ];
                        
                        for (var s = 0; s < buttonSelectors.length; s++) {
                            try {
                                var elements = document.querySelectorAll(buttonSelectors[s]);
                                for (var b = 0; b < elements.length; b++) {
                                    var element = elements[b];
                                    var text = element.textContent.trim().toLowerCase();
                                    var href = element.href || '';
                                    var onclick = element.getAttribute('onclick') || '';
                                    
                                    if (element.offsetParent !== null && 
                                        (text.includes('подтвердить') || 
                                         text.includes('просмотр') ||
                                         text.includes('confirm') ||
                                         text.includes('ok') ||
                                         href.includes('vlss?view=ok') ||
                                         href.includes('view=ok') ||
                                         onclick.includes('view=ok') ||
                                         onclick.includes('vlss'))) {
                                        result.button_found = true;
                                        result.button_element = element;
                                        break;
                                    }
                                }
                                if (result.button_found) break;
                            } catch (e) {
                                // Пропускаем ошибки
                            }
                        }
                        
                        return result;
                    """)
                    
                    # Если найдена кнопка - кликаем
                    if frame_status.get('button_found', False):
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", frame_status['button_element'])
                            time.sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", frame_status['button_element'])
                            logging.info("✅ Нажата кнопка подтверждения")
                            time.sleep(2)
                            result['button_found'] = True
                            self.driver.switch_to.default_content()
                            return result
                        except Exception as e:
                            logging.error(f"❌ Ошибка клика по кнопке: {e}")
                    
                    if frame_status.get('timer_found', False):
                        result['timer_found'] = True
                        result['timer_value'] = frame_status.get('timer_value')
                    
                    # Возвращаемся к основному документу
                    self.driver.switch_to.default_content()
                    result['iframe_switched'] = False
                    
                    # Если нашли таймер - возвращаем результат
                    if result['timer_found']:
                        return result
                    
                except Exception as e:
                    try:
                        self.driver.switch_to.default_content()
                        result['iframe_switched'] = False
                    except:
                        pass
                    continue
            
            return result
            
        except Exception as e:
            logging.error(f"❌ Ошибка поиска в frame: {e}")
            try:
                if result.get('iframe_switched', False):
                    self.driver.switch_to.default_content()
            except:
                pass
            return result

class LetterTaskHandler:
    """Класс для обработки заданий на чтение писем"""
    
    def __init__(self, driver, base_url, gpt_manager):
        self.driver = driver
        self.base_url = base_url
        self.gpt_manager = gpt_manager
        self.failed_task_ids = set()  # Отслеживание заданий с ошибками
        self.error_tasks = set()  # Отслеживание заданий с ошибками заявок
    
    def get_tasks(self) -> List[Dict]:
        """Получение заданий на чтение писем с подсчетом общего заработка и фильтрацией ошибочных"""
        logging.info("📧 Поиск заданий на чтение писем...")
        
        try:
            if "/tasks-letter" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/tasks-letter")
                time.sleep(1)
            
            letter_tasks_data = self.driver.execute_script("""
                var tasks = [];
                var totalEarnings = 0;
                var errorTasks = [];
                var startDivs = document.querySelectorAll("div[id^='start-mails-']");
                
                for (var i = 0; i < startDivs.length; i++) {
                    try {
                        var startDiv = startDivs[i];
                        var taskIdMatch = startDiv.id.match(/start-mails-(\\d+)/);
                        
                        if (taskIdMatch) {
                            var taskId = taskIdMatch[1];
                            
                            // Проверяем наличие ошибки заявки
                            var row = startDiv.closest('tr');
                            var errorElement = row ? row.querySelector('.start-error-serf') : null;
                            if (errorElement && errorElement.offsetParent !== null) {
                                errorTasks.push(taskId);
                                continue; // Пропускаем задания с ошибкой
                            }
                            
                            var link = startDiv.querySelector("a");
                            var title = link ? link.textContent.trim() : 'unknown';
                            var url = link ? link.getAttribute('title') : 'unknown';
                            
                            // Парсим стоимость чтения
                            var price = 0;
                            if (row) {
                                var priceElement = row.querySelector('td[style*="text-align:right"] span[title="Стоимость чтения"]');
                                if (priceElement) {
                                    var priceText = priceElement.textContent.trim();
                                    var priceMatch = priceText.match(/([0-9.,]+)/);
                                    if (priceMatch) {
                                        price = parseFloat(priceMatch[1].replace(',', '.'));
                                        totalEarnings += price;
                                    }
                                }
                            }
                            
                            tasks.push({
                                id: taskId,
                                title: title,
                                url: url,
                                price: price,
                                start_div_id: startDiv.id
                            });
                        }
                    } catch (e) {
                        // Пропускаем ошибочные элементы
                    }
                }
                
                return {
                    tasks: tasks,
                    totalEarnings: totalEarnings,
                    errorTasks: errorTasks
                };
            """)
            
            tasks = []
            total_earnings = letter_tasks_data.get('totalEarnings', 0)
            error_tasks = letter_tasks_data.get('errorTasks', [])
            
            # Обновляем список заданий с ошибками
            self.error_tasks.update(error_tasks)
            
            for task_data in letter_tasks_data.get('tasks', []):
                try:
                    task_id = task_data['id']
                    
                    # Пропускаем задания, которые уже имели ошибки
                    if task_id in self.failed_task_ids:
                        continue
                    
                    task_info = {
                        'id': task_data['id'],
                        'title': task_data['title'],
                        'url': task_data['url'],
                        'price': task_data['price'],
                        'start_div_id': task_data['start_div_id']
                    }
                    tasks.append(task_info)
                except Exception as e:
                    logging.debug(f"⚠ Ошибка создания задания письма: {e}")
                    continue
            
            # Информация о найденных заданиях
            logging.info(f"📧 Найдено заданий на письма: {len(tasks)}")
            if error_tasks:
                logging.info(f"⚠ Заданий с ошибками заявок: {len(error_tasks)}")
            if self.failed_task_ids:
                logging.info(f"⚠ Заданий с предыдущими ошибками: {len(self.failed_task_ids)}")
            logging.info(f"💰 Общий заработок за письма: {total_earnings:.4f} руб.")
            
            return tasks
            
        except Exception as e:
            logging.error(f"❌ Ошибка получения заданий писем: {e}")
            return []
    
    def execute_task(self, task: Dict) -> bool:
        """Выполнение задания на чтение письма"""
        task_id = task['id']
        logging.info(f"📧 Письмо задание {task_id}: {task['title'][:50]}...")
        
        original_window = self.driver.current_window_handle
        
        try:
            if "/tasks-letter" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/tasks-letter")
                time.sleep(1)
            
            # Прокручиваем к элементу перед работой с ним
            try:
                start_div = self.driver.find_element(By.ID, task['start_div_id'])
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", start_div)
                time.sleep(1)
                start_link = start_div.find_element(By.TAG_NAME, "a")
            except NoSuchElementException:
                logging.warning(f"⚠ Элементы письмо задания {task_id} не найдены")
                return False
            except Exception as e:
                logging.error(f"❌ Ошибка поиска элементов письмо задания {task_id}: {e}")
                return False
            
            # Случайная задержка перед кликом
            pause = random.uniform(1, 3)
            logging.info(f"⏳ Случайная пауза перед кликом {pause:.1f}с")
            time.sleep(pause)
            
            try:
                start_link.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", start_link)
            
            time.sleep(2)
            
            # Проверка ошибки заявки для конкретного задания
            if self.check_task_error_for_current_task(task_id):
                logging.warning(f"⚠ Ошибка заявки для задания {task_id}, переходим к следующему")
                self.failed_task_ids.add(task_id)
                self.error_tasks.add(task_id)
                return False
            
            wait = WebDriverWait(self.driver, 15)
            
            # Исправление: Используем JavaScript клик для перекрытой кнопки
            try:
                start_reading_button = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.start-yes-serf"))
                )
                
                # Прокручиваем к кнопке
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", start_reading_button)
                time.sleep(0.5)
                
                # Случайная задержка перед подтверждением чтения
                confirm_pause = random.uniform(0.5, 2)
                logging.info(f"⏳ Случайная пауза перед подтверждением чтения: {confirm_pause:.1f}с")
                time.sleep(confirm_pause)
                
                # Принудительный клик через JavaScript
                self.driver.execute_script("arguments[0].click();", start_reading_button)
                logging.info("✅ Нажата кнопка 'Приступить к чтению' (JavaScript клик)")
                
            except Exception as e:
                # Повторная проверка ошибки если кнопка не найдена
                if self.check_task_error_for_current_task(task_id):
                    logging.warning(f"⚠ Ошибка заявки для задания {task_id} при ожидании кнопки")
                    self.failed_task_ids.add(task_id)
                    self.error_tasks.add(task_id)
                    return False
                
                logging.error(f"❌ Не найдена кнопка 'Приступить к чтению': {e}")
                return False
            
            time.sleep(3)
            
            # Извлечение данных письма
            letter_data = self.extract_letter_data()
            if not letter_data:
                logging.error("❌ Не удалось извлечь данные письма")
                return False
            
            # Имитация чтения
            reading_time = HumanBehaviorSimulator.calculate_reading_time(
                letter_data['text'] + letter_data['question'] + " ".join(letter_data['answers'])
            )
            
            logging.info(f"📚 Имитация чтения письма ({reading_time:.1f}с)...")
            time.sleep(reading_time)
            
            # Получение ответа от GPT
            gpt_answer = self.gpt_manager.ask_gpt(
                letter_data['text'], 
                letter_data['question'], 
                letter_data['answers']
            )
            
            # Проверка успешности получения ответа
            if gpt_answer is None:
                logging.error("❌ Не удалось получить ответ от GPT. Пропускаем задание.")
                return False
            
            # Клик по выбранному ответу
            try:
                answer_index = int(gpt_answer) - 1
                if 0 <= answer_index < len(letter_data['answer_links']):
                    selected_link = letter_data['answer_links'][answer_index]
                    logging.info(f"🤖 Выбираю ответ {gpt_answer}: {letter_data['answers'][answer_index][:30]}...")
                    
                    # Прокручиваем к ответу
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", selected_link)
                    time.sleep(0.5)
                    
                    selected_link.click()
                    time.sleep(3)  # Ждем после клика
                    
                    # Проверяем новое окно/вкладку
                    windows = self.driver.window_handles
                    if len(windows) > 1:
                        logging.info(f"🔄 Обнаружено {len(windows)} окон, переключаемся...")
                        for window in windows:
                            if window != original_window:
                                self.driver.switch_to.window(window)
                                logging.info(f"🔄 Переключились на новое окно: {self.driver.current_url}")
                                break
                    
                    # Новый метод поиска таймера и капчи
                    if self.handle_timer_and_captcha():
                        logging.info("✅ Письмо задание завершено!")
                        
                        # Возвращаемся в исходное окно
                        if self.driver.current_window_handle != original_window:
                            self.driver.switch_to.window(original_window)
                        
                        # Закрываем все лишние вкладки
                        self.close_extra_tabs(original_window)
                        
                        # НОВОЕ: Обновляем страницу заданий после возврата
                        logging.info("🔄 Обновление страницы заданий на чтение писем...")
                        self.driver.refresh()
                        time.sleep(2)
                        
                        # НОВОЕ: Повторный парсинг заданий после обновления
                        logging.info("🔄 Повторный парсинг заданий после обновления...")
                        updated_tasks = self.get_tasks()
                        logging.info(f"📊 После обновления найдено заданий: {len(updated_tasks)}")
                        
                        return True
                    else:
                        logging.error("❌ Ошибка завершения письма")
                        return False
                else:
                    logging.error(f"❌ Неверный индекс ответа: {gpt_answer}")
                    return False
            except ValueError:
                logging.error(f"❌ Некорректный ответ от GPT: {gpt_answer}")
                return False
            except Exception as e:
                logging.error(f"❌ Ошибка обработки ответа GPT: {e}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Ошибка письмо задания {task_id}: {e}")
            return False
        finally:
            # Закрываем лишние вкладки в случае ошибки
            try:
                self.close_extra_tabs(original_window)
            except Exception as cleanup_error:
                logging.debug(f"⚠ Ошибка закрытия вкладок при очистке: {cleanup_error}")
    
    def check_task_error_for_current_task(self, task_id: str) -> bool:
        """Проверка ошибки заявки для конкретного задания"""
        try:
            # Ищем ошибку в контексте конкретного задания
            error_check_result = self.driver.execute_script("""
                var taskId = arguments[0];
                var result = {
                    has_error: false,
                    error_text: '',
                    task_specific_error: false
                };
                
                // Проверяем общие ошибки
                var generalErrors = document.querySelectorAll('.start-error-serf');
                for (var i = 0; i < generalErrors.length; i++) {
                    var errorElement = generalErrors[i];
                    if (errorElement.offsetParent !== null) {
                        result.has_error = true;
                        result.error_text = errorElement.textContent.trim();
                        
                        // Проверяем, связана ли ошибка с нашим заданием
                        var parentRow = errorElement.closest('tr');
                        if (parentRow) {
                            var taskDiv = parentRow.querySelector('#start-mails-' + taskId);
                            if (taskDiv) {
                                result.task_specific_error = true;
                                break;
                            }
                        }
                    }
                }
                
                return result;
            """, task_id)
            
            if error_check_result['task_specific_error']:
                logging.info(f"🚫 Найдена ошибка для задания {task_id}: {error_check_result['error_text']}")
                return True
            elif error_check_result['has_error']:
                logging.debug(f"ℹ Найдена общая ошибка (не для задания {task_id}): {error_check_result['error_text']}")
                return False
            else:
                return False
                
        except Exception as e:
            logging.debug(f"⚠ Ошибка проверки элемента ошибки для задания {task_id}: {e}")
            return False
    
    def check_all_tasks_failed(self, available_tasks: List[Dict]) -> bool:
        """Проверка что все задания завершились ошибкой"""
        if not available_tasks:
            return True
        
        available_task_ids = set(task['id'] for task in available_tasks)
        failed_count = len(self.failed_task_ids.intersection(available_task_ids))
        
        if failed_count == len(available_tasks):
            logging.info(f"⚠ Все {len(available_tasks)} заданий писем завершились ошибкой, считаем выполненными")
            return True
        
        return False
    
    def has_available_tasks(self) -> bool:
        """Проверка наличия доступных заданий (без ошибок)"""
        try:
            if "/tasks-letter" not in self.driver.current_url:
                self.driver.get(f"{self.base_url}/tasks-letter")
                time.sleep(1)
            
            # Получаем информацию о всех заданиях и их ошибках
            task_status = self.driver.execute_script("""
                var totalTasks = 0;
                var errorTasks = 0;
                var availableTasks = 0;
                var startDivs = document.querySelectorAll("div[id^='start-mails-']");
                
                for (var i = 0; i < startDivs.length; i++) {
                    try {
                        var startDiv = startDivs[i];
                        var taskIdMatch = startDiv.id.match(/start-mails-(\\d+)/);
                        
                        if (taskIdMatch) {
                            var taskId = taskIdMatch[1];
                            totalTasks++;
                            
                            // Проверяем наличие ошибки заявки
                            var row = startDiv.closest('tr');
                            var errorElement = row ? row.querySelector('.start-error-serf') : null;
                            if (errorElement && errorElement.offsetParent !== null) {
                                errorTasks++;
                            } else {
                                availableTasks++;
                            }
                        }
                    } catch (e) {
                        // Пропускаем ошибочные элементы
                    }
                }
                
                return {
                    totalTasks: totalTasks,
                    errorTasks: errorTasks,
                    availableTasks: availableTasks
                };
            """)
            
            total_tasks = task_status.get('totalTasks', 0)
            error_tasks = task_status.get('errorTasks', 0)
            available_tasks = task_status.get('availableTasks', 0)
            
            logging.info(f"📊 Статус заданий писем: всего={total_tasks}, ошибки={error_tasks}, доступно={available_tasks}")
            
            # Если все задания имеют ошибки и общее количество > 0
            if total_tasks > 0 and error_tasks == total_tasks:
                logging.info("🚫 Все задания писем имеют ошибки заявок, переходим к следующему типу")
                return False
            
            return available_tasks > 0
            
        except Exception as e:
            logging.error(f"❌ Ошибка проверки доступности заданий: {e}")
            return False
    
    def close_extra_tabs(self, original_window):
        """Закрытие всех лишних вкладок кроме исходной"""
        try:
            current_windows = self.driver.window_handles
            
            if len(current_windows) > 1:
                logging.info(f"🗂 Закрытие {len(current_windows) - 1} лишних вкладок...")
                
                for window in current_windows:
                    if window != original_window:
                        try:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                        except:
                            pass
                
                # Переключаемся обратно на исходную вкладку
                try:
                    self.driver.switch_to.window(original_window)
                    logging.info("✅ Все лишние вкладки закрыты")
                except:
                    # Если исходная вкладка была закрыта, переключаемся на первую доступную
                    available_windows = self.driver.window_handles
                    if available_windows:
                        self.driver.switch_to.window(available_windows[0])
                        logging.info("✅ Переключились на первую доступную вкладку")
                    
        except Exception as e:
            logging.debug(f"⚠ Ошибка закрытия лишних вкладок: {e}")
    
    def extract_letter_data(self) -> Optional[Dict]:
        """Извлечение данных письма (текст, вопрос, ответы)"""
        try:
            letter_data = self.driver.execute_script("""
                var container = document.querySelector('.mails-earn-view-container');
                if (!container) return null;
                
                // Извлекаем текст письма
                var textDiv = container.querySelector('div[style*="padding:10px"]');
                var letterText = textDiv ? textDiv.textContent.trim() : '';
                
                // Извлекаем вопрос
                var questionDiv = container.querySelector('.tiket b');
                var question = questionDiv ? questionDiv.parentNode.textContent.replace('Вопрос:', '').trim() : '';
                
                // Извлекаем ответы
                var answerContainer = container.querySelector('.mails-otvet-new');
                var answerLinks = answerContainer ? answerContainer.querySelectorAll('a') : [];
                var answers = [];
                
                for (var i = 0; i < answerLinks.length; i++) {
                    answers.push(answerLinks[i].textContent.trim());
                }
                
                return {
                    text: letterText,
                    question: question,
                    answers: answers
                };
            """)
            
            if letter_data and letter_data['text'] and letter_data['question'] and letter_data['answers']:
                # Получаем элементы ссылок для клика
                answer_links = self.driver.find_elements(By.CSS_SELECTOR, ".mails-otvet-new a")
                
                result = {
                    'text': letter_data['text'],
                    'question': letter_data['question'],
                    'answers': letter_data['answers'],
                    'answer_links': answer_links
                }
                
                logging.info(f"📧 Письмо: {len(result['text'])} символов, {len(result['answers'])} ответов")
                return result
            
            return None
            
        except Exception as e:
            logging.error(f"❌ Ошибка извлечения данных письма: {e}")
            return None
    
    def handle_timer_and_captcha(self) -> bool:
        """Поиск таймера и капчи с рекурсивным обходом фреймов"""
        logging.info(f"🔍 Поиск таймера (#tmr) или капчи (input[name='code'][type='range']) на странице: {self.driver.current_url}")
        
        try:
            # Ждём полной загрузки страницы
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logging.info("✅ Страница полностью загружена")
            
            max_wait_time = 90  # Максимальное время ожидания (сек)
            check_interval = 0.3  # Интервал проверки (сек)
            elapsed_time = 0
            last_timer_text = ""
            
            while elapsed_time < max_wait_time:
                # Проверяем основной документ
                try:
                    timer = WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.ID, "tmr"))
                    )
                    timer_text = timer.text.strip()
                    timer_value = int(''.join(filter(str.isdigit, timer_text))) if any(c.isdigit() for c in timer_text) else -1
                    if timer_text != last_timer_text:
                        print(f"\r⏰ Таймер в основном документе: {timer_text} ({timer_value}с)", end="", flush=True)
                        last_timer_text = timer_text
                    
                    if timer_value <= 0:
                        print()  # Перевод строки после таймера
                        logging.info("✅ Таймер завершён, ищем капчу...")
                    else:
                        time.sleep(check_interval)
                        elapsed_time += check_interval
                        continue
                except TimeoutException:
                    pass
                
                # Проверяем капчу в основном документе
                try:
                    slider = WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='code'][type='range']"))
                    )
                    max_value = self.driver.execute_script("return arguments[0].getAttribute('max');", slider)
                    max_value = int(max_value) if max_value and max_value.isdigit() else 1000
                    logging.info(f"🔐 Капча найдена в основном документе, max={max_value}")
                    
                    # Случайная пауза перед началом работы с капчей
                    captcha_pause = random.uniform(1, 3)
                    logging.info(f"⏳ Пауза перед капчей: {captcha_pause:.1f}с")
                    time.sleep(captcha_pause)
                    
                    # Кривой человеческий ползунок
                    steps = random.randint(5, 15)
                    current_value = int(self.driver.execute_script("return arguments[0].value;", slider) or 0)
                    step_values = []
                    remaining = max_value - current_value
                    for _ in range(steps - 1):
                        step = random.randint(1, int(remaining / 2)) if remaining > 0 else 0
                        step_values.append(step)
                        remaining -= step
                    step_values.append(remaining)  # Последний шаг до конца
                    
                    for step in step_values:
                        current_value += step
                        self.driver.execute_script("""
                            var slider = arguments[0];
                            slider.value = arguments[1];
                            slider.dispatchEvent(new Event('input', { bubbles: true }));
                            slider.dispatchEvent(new Event('change', { bubbles: true }));
                        """, slider, current_value)
                        time.sleep(random.uniform(0.05, 0.3))
                    
                    logging.info(f"✅ Ползунок капчи перемещён на {max_value} за {steps} шагов")
                    
                    # Пауза перед кликом по кнопке
                    button_pause = random.uniform(0.5, 2)
                    logging.info(f"⏳ Пауза перед кнопкой 'Отправить': {button_pause:.1f}с")
                    time.sleep(button_pause)
                    
                    # Клик по кнопке "Отправить"
                    button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[text()='Отправить' or text()='Submit']"))
                    )
                    self.driver.execute_script("arguments[0].click();", button)
                    logging.info("✅ Кнопка 'Отправить' нажата")
                    time.sleep(2)
                    return True
                except TimeoutException:
                    pass
                
                # Рекурсивный поиск по фреймам
                frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
                
                for frame in frames:
                    try:
                        self.driver.switch_to.frame(frame)
                        
                        # Проверяем таймер во фрейме
                        try:
                            timer = WebDriverWait(self.driver, 1).until(
                                EC.presence_of_element_located((By.ID, "tmr"))
                            )
                            timer_text = timer.text.strip()
                            timer_value = int(''.join(filter(str.isdigit, timer_text))) if any(c.isdigit() for c in timer_text) else -1
                            if timer_text != last_timer_text:
                                print(f"\r⏰ Таймер во фрейме: {timer_text} ({timer_value}с)", end="", flush=True)
                                last_timer_text = timer_text
                            
                            if timer_value <= 0:
                                print()  # Перевод строки после таймера
                                logging.info("✅ Таймер завершён, ищем капчу...")
                            else:
                                self.driver.switch_to.default_content()
                                time.sleep(check_interval)
                                elapsed_time += check_interval
                                continue
                        except TimeoutException:
                            pass
                        
                        # Проверяем капчу во фрейме
                        try:
                            slider = WebDriverWait(self.driver, 1).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='code'][type='range']"))
                            )
                            max_value = self.driver.execute_script("return arguments[0].getAttribute('max');", slider)
                            max_value = int(max_value) if max_value and max_value.isdigit() else 1000
                            logging.info(f"🔐 Капча найдена во фрейме, max={max_value}")
                            
                            # Случайная пауза перед началом работы с капчей
                            captcha_pause = random.uniform(1, 3)
                            logging.info(f"⏳ Пауза перед капчей: {captcha_pause:.1f}с")
                            time.sleep(captcha_pause)
                            
                            # Кривой человеческий ползунок
                            steps = random.randint(5, 15)
                            current_value = int(self.driver.execute_script("return arguments[0].value;", slider) or 0)
                            step_values = []
                            remaining = max_value - current_value
                            for _ in range(steps - 1):
                                step = random.randint(1, int(remaining / 2)) if remaining > 0 else 0
                                step_values.append(step)
                                remaining -= step
                            step_values.append(remaining)
                            
                            for step in step_values:
                                current_value += step
                                self.driver.execute_script("""
                                    var slider = arguments[0];
                                    slider.value = arguments[1];
                                    slider.dispatchEvent(new Event('input', { bubbles: true }));
                                    slider.dispatchEvent(new Event('change', { bubbles: true }));
                                """, slider, current_value)
                                time.sleep(random.uniform(0.05, 0.3))
                            
                            logging.info(f"✅ Ползунок капчи перемещён на {max_value} за {steps} шагов")
                            
                            # Пауза перед кликом по кнопке
                            button_pause = random.uniform(0.5, 2)
                            logging.info(f"⏳ Пауза перед кнопкой 'Отправить': {button_pause:.1f}с")
                            time.sleep(button_pause)
                            
                            # Клик по кнопке "Отправить"
                            button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[text()='Отправить' or text()='Submit']"))
                            )
                            self.driver.execute_script("arguments[0].click();", button)
                            logging.info("✅ Кнопка 'Отправить' нажата")
                            self.driver.switch_to.default_content()
                            time.sleep(2)
                            return True
                        except TimeoutException:
                            pass
                            
                        # Рекурсивный поиск вложенных фреймов
                        nested_frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
                        if nested_frames:
                            for nested_frame in nested_frames:
                                try:
                                    self.driver.switch_to.frame(nested_frame)
                                    
                                    # Проверяем таймер во вложенном фрейме
                                    try:
                                        timer = WebDriverWait(self.driver, 1).until(
                                            EC.presence_of_element_located((By.ID, "tmr"))
                                        )
                                        timer_text = timer.text.strip()
                                        timer_value = int(''.join(filter(str.isdigit, timer_text))) if any(c.isdigit() for c in timer_text) else -1
                                        if timer_text != last_timer_text:
                                            print(f"\r⏰ Таймер во вложенном фрейме: {timer_text} ({timer_value}с)", end="", flush=True)
                                            last_timer_text = timer_text
                                        
                                        if timer_value <= 0:
                                            print()  # Перевод строки после таймера
                                            logging.info("✅ Таймер завершён, ищем капчу...")
                                        else:
                                            self.driver.switch_to.default_content()
                                            time.sleep(check_interval)
                                            elapsed_time += check_interval
                                            continue
                                    except TimeoutException:
                                        pass
                                    
                                    # Проверяем капчу во вложенном фрейме
                                    try:
                                        slider = WebDriverWait(self.driver, 1).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='code'][type='range']"))
                                        )
                                        max_value = self.driver.execute_script("return arguments[0].getAttribute('max');", slider)
                                        max_value = int(max_value) if max_value and max_value.isdigit() else 1000
                                        logging.info(f"🔐 Капча найдена во вложенном фрейме, max={max_value}")
                                        
                                        # Случайная пауза перед началом работы с капчей
                                        captcha_pause = random.uniform(1, 3)
                                        logging.info(f"⏳ Пауза перед капчей: {captcha_pause:.1f}с")
                                        time.sleep(captcha_pause)
                                        
                                        # Кривой человеческий ползунок
                                        steps = random.randint(5, 15)
                                        current_value = int(self.driver.execute_script("return arguments[0].value;", slider) or 0)
                                        step_values = []
                                        remaining = max_value - current_value
                                        for _ in range(steps - 1):
                                            step = random.randint(1, int(remaining / 2)) if remaining > 0 else 0
                                            step_values.append(step)
                                            remaining -= step
                                        step_values.append(remaining)
                                        
                                        for step in step_values:
                                            current_value += step
                                            self.driver.execute_script("""
                                                var slider = arguments[0];
                                                slider.value = arguments[1];
                                                slider.dispatchEvent(new Event('input', { bubbles: true }));
                                                slider.dispatchEvent(new Event('change', { bubbles: true }));
                                            """, slider, current_value)
                                            time.sleep(random.uniform(0.05, 0.3))
                                        
                                        logging.info(f"✅ Ползунок капчи перемещён на {max_value} за {steps} шагов")
                                        
                                        # Пауза перед кликом по кнопке
                                        button_pause = random.uniform(0.5, 2)
                                        logging.info(f"⏳ Пауза перед кнопкой 'Отправить': {button_pause:.1f}с")
                                        time.sleep(button_pause)
                                        
                                        # Клик по кнопке "Отправить"
                                        button = WebDriverWait(self.driver, 5).until(
                                            EC.element_to_be_clickable((By.XPATH, "//button[text()='Отправить' or text()='Submit']"))
                                        )
                                        self.driver.execute_script("arguments[0].click();", button)
                                        logging.info("✅ Кнопка 'Отправить' нажата")
                                        self.driver.switch_to.default_content()
                                        time.sleep(2)
                                        return True
                                    except TimeoutException:
                                        pass
                                    
                                    self.driver.switch_to.default_content()
                                except:
                                    self.driver.switch_to.default_content()
                                    continue
                            
                        self.driver.switch_to.default_content()
                    except:
                        self.driver.switch_to.default_content()
                        continue
                
                # Логирование прогресса
                if elapsed_time % 10 == 0:
                    logging.info(f"🔍 Поиск таймера/капчи... ({elapsed_time}/{max_wait_time}с)")
                
                time.sleep(check_interval)
                elapsed_time += check_interval
            
            print()  # Перевод строки, чтобы не оставлять курсор в конце
            logging.warning("⚠ Не удалось найти таймер или капчу за отведённое время")
            return False
            
        except Exception as e:
            print()  # Перевод строки на случай ошибки
            logging.error(f"❌ Ошибка обработки таймера/капчи: {e}")
            return False

class LoginHandler:
    """Класс для обработки авторизации"""
    
    def __init__(self, driver, base_url, username, password):
        self.driver = driver
        self.base_url = base_url
        self.username = username
        self.password = password
        self.cookies_file = "aviso_cookies.pkl"
    
    def check_authorization(self) -> bool:
        """Проверка авторизации через поиск профиля"""
        try:
            # Даем время для загрузки страницы
            time.sleep(1)  # Ускорено
            
            # Проверяем наличие блока профиля
            profile_found = self.driver.execute_script("""
                // Ищем блок с информацией о пользователе
                var userBlock = document.querySelector('.user-block__info');
                if (userBlock) {
                    // Ищем ID, ник и статус
                    var userIdElement = document.querySelector('#user-block-info-userid');
                    var usernameElement = document.querySelector('#user-block-info-username');
                    var statusElement = document.querySelector('.user-block-info__item .info_value a');
                    
                    if (userIdElement && usernameElement) {
                        return {
                            authorized: true,
                            user_id: userIdElement.textContent.trim(),
                            username: usernameElement.textContent.trim(),
                            status: statusElement ? statusElement.textContent.trim() : 'unknown'
                        };
                    }
                }
                
                // Дополнительная проверка - поиск элементов профиля
                var profileElements = document.querySelectorAll('[class*="user"], [id*="user"], [class*="profile"], [id*="profile"]');
                var hasProfile = false;
                
                for (var i = 0; i < profileElements.length; i++) {
                    var element = profileElements[i];
                    var text = element.textContent.toLowerCase();
                    
                    // Проверяем на наличие индикаторов авторизации
                    if (text.includes('профиль') || text.includes('balance') || text.includes('баланс') || 
                        text.includes('выйти') || text.includes('logout') || text.includes('настройки')) {
                        hasProfile = true;
                        break;
                    }
                }
                
                // Проверяем отсутствие форм логина
                var loginForms = document.querySelectorAll('input[name="username"], input[name="login"], input[name="password"]');
                var hasLoginForm = false;
                
                for (var i = 0; i < loginForms.length; i++) {
                    if (loginForms[i].offsetParent !== null) {
                        hasLoginForm = true;
                        break;
                    }
                }
                
                return {
                    authorized: hasProfile && !hasLoginForm,
                    user_id: null,
                    username: null,
                    status: null,
                    debug: {
                        hasProfile: hasProfile,
                        hasLoginForm: hasLoginForm,
                        url: window.location.href,
                        title: document.title
                    }
                };
            """)
            
            if profile_found.get('authorized', False):
                if profile_found.get('user_id') and profile_found.get('username'):
                    logging.info(f"✅ Авторизован: ID={profile_found['user_id']}, Ник={profile_found['username']}, Статус={profile_found['status']}")
                else:
                    logging.info("✅ Авторизован (профиль найден)")
                return True
            else:
                debug_info = profile_found.get('debug', {})
                logging.info(f"❌ Не авторизован - URL: {debug_info.get('url', 'unknown')}")
                logging.info(f"   Заголовок: {debug_info.get('title', 'unknown')}")
                logging.info(f"   Есть профиль: {debug_info.get('hasProfile', False)}")
                logging.info(f"   Есть форма логина: {debug_info.get('hasLoginForm', False)}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Ошибка проверки авторизации: {e}")
            return False
    
    def login(self) -> bool:
        """Авторизация"""
        logging.info("🔐 Авторизация...")
        
        try:
            self.driver.get(f"{self.base_url}/login")
            time.sleep(2)  # Ускорено
            
            # Проверяем что мы действительно на странице логина
            current_url = self.driver.current_url
            if "/login" not in current_url:
                logging.error(f"❌ Не удалось перейти на страницу логина. Текущий URL: {current_url}")
                return False
            
            # ИЗМЕНЕНИЕ 1: Уменьшаем таймаут поиска элементов
            wait = WebDriverWait(self.driver, 15)
            
            # Находим поля для ввода
            try:
                logging.info("🔍 Поиск элементов формы...")
                username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                password_field = self.driver.find_element(By.NAME, "password")
                login_button = self.driver.find_element(By.ID, "button-login")
                logging.info("✅ Элементы формы найдены")
            except Exception as e:
                logging.error(f"❌ Не найдены элементы формы логина: {e}")
                return False
            
            # Вводим логин
            logging.info("⌨️ Ввод логина...")
            username_field.click()
            time.sleep(0.2)  # Ускорено
            HumanBehaviorSimulator.human_like_typing(username_field, self.username, self.driver)
            
            # Вводим пароль
            logging.info("⌨️ Ввод пароля...")
            password_field.click()
            time.sleep(0.2)  # Ускорено
            HumanBehaviorSimulator.human_like_typing(password_field, self.password, self.driver)
            
            # Случайная пауза перед входом
            pause_time = random.uniform(0.5, 1.5)  # Ускорено
            logging.info(f"⏳ Пауза перед входом: {pause_time:.1f}с")
            time.sleep(pause_time)
            
            # Нажимаем кнопку входа
            try:
                logging.info("🔘 Нажимаем кнопку входа...")
                login_button.click()
                logging.info("✅ Нажата кнопка входа")
            except Exception as e:
                logging.error(f"❌ Ошибка нажатия кнопки входа: {e}")
                # Пробуем через JavaScript
                try:
                    self.driver.execute_script("arguments[0].click();", login_button)
                    logging.info("✅ Нажата кнопка входа через JavaScript")
                except Exception as e2:
                    logging.error(f"❌ Ошибка нажатия кнопки входа через JavaScript: {e2}")
                    return False
            
            # ИЗМЕНЕНИЕ 2: Увеличиваем время ожидания результата
            logging.info("⏳ Ожидание результата авторизации...")
            time.sleep(10)  # Было 3, стало 10
            
            # Проверяем URL после входа
            current_url = self.driver.current_url
            logging.info(f"🔍 URL после входа: {current_url}")
            
            # Проверка 2FA если требуется
            if "/2fa" in current_url:
                logging.info("🔐 Требуется 2FA код")
                
                try:
                    code_field = wait.until(EC.presence_of_element_located((By.NAME, "code")))
                    
                    verification_code = input("Введите 2FA код: ").strip()
                    
                    if verification_code and verification_code.isdigit():
                        code_field.click()
                        HumanBehaviorSimulator.human_like_typing(code_field, verification_code, self.driver)
                        
                        confirm_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.button_theme_blue")
                        if confirm_buttons:
                            confirm_buttons[0].click()
                        
                        time.sleep(10)  # Было 3, стало 10
                    
                except Exception as e:
                    logging.error(f"❌ Ошибка 2FA: {e}")
                    return False
            
            # Проверка результата через профиль
            logging.info("🔍 Проверка авторизации...")
            if self.check_authorization():
                logging.info("✅ Авторизация успешна")
                self.save_cookies()
                return True
            else:
                logging.error("❌ Авторизация не удалась - профиль не найден")
                
                # Дополнительная диагностика
                page_source = self.driver.page_source
                if "неверный логин" in page_source.lower() or "неверный пароль" in page_source.lower():
                    logging.error("❌ Неверные учетные данные")
                elif "заблокирован" in page_source.lower():
                    logging.error("❌ Аккаунт заблокирован")
                else:
                    logging.error("❌ Неизвестная ошибка авторизации")
                
                return False
                
        except Exception as e:
            logging.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    def save_cookies(self):
        """Сохранение cookies"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения cookies: {e}")
    
    def load_cookies(self) -> bool:
        """Загрузка cookies"""
        try:
            if os.path.exists(self.cookies_file):
                self.driver.get(self.base_url)
                time.sleep(2)  # Ускорено
                
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        pass
                
                return True
        except:
            pass
        
        return False

class AvisoAutomation:
    """Основной класс автоматизации Aviso"""
    
    def __init__(self):
        self.setup_logging()
        self.driver = None
        # self.tor_manager removed - browser now works without Tor
        self.ua_manager = UserAgentManager()
        self.gecko_manager = GeckoDriverManager()
        self.gpt_manager = GPTManager()
        self.task_coordinator = TaskCoordinator()
        # self.original_ip removed - no longer checking IP
        
        # Данные для авторизации
        self.username = "aleksey836"
        self.password = "123456"
        self.base_url = "https://aviso.bz"
        
        # Task handlers - removed YouTube handler
        # self.youtube_handler = None - removed
        self.surf_handler = None
        self.letter_handler = None
        self.login_handler = None
        
        logging.info("🚀 Запуск Aviso Bot без Tor")
        
    def setup_logging(self):
        """Настройка логирования"""
        log_filename = f"aviso_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_format = "%(asctime)s [%(levelname)s] %(message)s"
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_filename, encoding='utf-8')
            ]
        )

    # IP checking methods removed - no longer needed without Tor

    def find_firefox_binary(self) -> Optional[str]:
        """Поиск Firefox"""
        possible_paths = []
        
        # Detect system and termux without tor_manager
        system = platform.system().lower()
        is_termux = 'com.termux' in os.environ.get('PREFIX', '') or '/data/data/com.termux' in os.environ.get('HOME', '')
        
        if is_termux:
            possible_paths = [
                '/data/data/com.termux/files/usr/bin/firefox',
                f"{os.environ.get('PREFIX', '')}/bin/firefox"
            ]
        elif system == 'linux':
            possible_paths = [
                '/usr/bin/firefox',
                '/usr/local/bin/firefox',
                '/opt/firefox/firefox',
                '/snap/bin/firefox'
            ]
        elif system == 'windows':
            possible_paths = [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
            ]
        elif system == 'darwin':
            possible_paths = [
                '/Applications/Firefox.app/Contents/MacOS/firefox'
            ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        # Check if firefox command exists in PATH
        try:
            if system == 'windows':
                result = subprocess.run(['where', 'firefox'], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', 'firefox'], capture_output=True, text=True)
            
            if result.returncode == 0:
                return 'firefox'
        except:
            pass
        
        return None

    def setup_driver(self) -> bool:
        """Настройка Firefox без Tor"""
        logging.info("🌐 Настройка браузера без Tor...")
        
        try:
            user_agent = self.ua_manager.get_user_agent(self.username)
            geckodriver_path = self.gecko_manager.get_driver_path()
            
            firefox_options = Options()
            
            # Настройка без прокси (обычное подключение)
            firefox_options.set_preference("network.proxy.type", 0)  # No proxy
            
            firefox_options.set_preference("general.useragent.override", user_agent)
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("network.http.use-cache", False)
            
            if "Android" in user_agent:
                firefox_options.set_preference("layout.css.devPixelRatio", "2.0")
                firefox_options.set_preference("dom.w3c_touch_events.enabled", 1)
            else:
                firefox_options.set_preference("layout.css.devPixelRatio", "2.0")
                firefox_options.set_preference("dom.w3c_touch_events.enabled", 1)
                firefox_options.set_preference("general.appname.override", "Netscape")
                firefox_options.set_preference("general.appversion.override", "5.0 (Mobile; rv:68.0)")
            
            firefox_options.set_preference("media.peerconnection.enabled", False)
            firefox_options.set_preference("media.navigator.enabled", False)
            firefox_options.set_preference("privacy.resistFingerprinting", False)
            firefox_options.set_preference("privacy.trackingprotection.enabled", True)
            firefox_options.set_preference("geo.enabled", False)
            firefox_options.set_preference("browser.safebrowsing.downloads.remote.enabled", False)
            firefox_options.set_preference("app.update.enabled", False)
            firefox_options.set_preference("toolkit.telemetry.enabled", False)
            firefox_options.set_preference("datareporting.healthreport.uploadEnabled", False)
            
            # Check if running in Termux (still needed for sandbox options)
            system = platform.system().lower()
            is_termux = 'com.termux' in os.environ.get('PREFIX', '') or '/data/data/com.termux' in os.environ.get('HOME', '')
            
            if is_termux:
                firefox_options.add_argument("--no-sandbox")
                firefox_options.add_argument("--disable-dev-shm-usage")
            
            firefox_binary = self.find_firefox_binary()
            if firefox_binary and firefox_binary != 'firefox':
                firefox_options.binary_location = firefox_binary
            
            service = Service(executable_path=geckodriver_path)
            self.driver = webdriver.Firefox(options=firefox_options, service=service)
            
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            if "Android" in user_agent:
                mobile_sizes = [(360, 640), (375, 667), (414, 896), (393, 851)]
                width, height = random.choice(mobile_sizes)
            else:
                ipad_sizes = [(768, 1024), (834, 1112), (1024, 1366)]
                width, height = random.choice(ipad_sizes)
            
            self.driver.set_window_size(width, height)
            logging.info("✅ Браузер запущен без Tor")
            
            # Инициализируем обработчики задач (без YouTube)
            # self.youtube_handler - removed
            self.surf_handler = SurfTaskHandler(self.driver, self.base_url)
            self.letter_handler = LetterTaskHandler(self.driver, self.base_url, self.gpt_manager)
            self.login_handler = LoginHandler(self.driver, self.base_url, self.username, self.password)
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка браузера: {e}")
            return False
    
    def execute_tasks_by_type(self, task_type: str) -> int:
        """Выполнение заданий со случайным выбором и перезагрузкой"""
        logging.info(f"🎯 Выполнение заданий типа: {task_type}")

        completed_tasks = 0
        max_attempts = 50
        attempt_count = 0
        
        try:
            while attempt_count < max_attempts:
                attempt_count += 1
            
                # ПОВТОРНЫЙ парсинг заданий перед каждой попыткой
                if task_type == 'surf':
                    tasks = self.surf_handler.get_tasks()
                    
                    # ПРАВИЛЬНАЯ ПРОВЕРКА: Все ли оставшиеся задания имеют ошибки
                    if tasks:
                        all_task_ids = set(task['id'] for task in tasks)
                        failed_task_ids = self.surf_handler.failed_task_ids
                        
                        # Если ВСЕ найденные задания есть в списке проваленных - прекращаем
                        if all_task_ids.issubset(failed_task_ids):
                            logging.info(f"🚫 Все {len(tasks)} оставшихся серфинг заданий уже имели ошибки заявок, переходим к следующему типу")
                            break
                    
                elif task_type == 'letters':
                    tasks = self.letter_handler.get_tasks()
                else:
                    logging.warning(f"⚠ Неизвестный тип заданий: {task_type}")
                    break
            
                if not tasks:
                    logging.info(f"ℹ Заданий типа {task_type} больше нет")
                    break
            
                # СЛУЧАЙНЫЙ выбор задания
                task = random.choice(tasks)
                task_id = task['id']
            
                logging.info(f"📝 {task_type.title()} {completed_tasks + 1} (ID: {task_id}) из {len(tasks)} доступных")
            
                # Выполняем задание
                success = False
                if task_type == 'surf':
                    success = self.surf_handler.execute_task(task)
                elif task_type == 'letters':
                    success = self.letter_handler.execute_task(task)
            
                if success:
                    completed_tasks += 1
                    logging.info(f"✅ Задание {task_id} завершено. Всего выполнено: {completed_tasks}")
                    self.inter_task_pause()
                else:
                    logging.warning(f"⚠ Задание {task_id} не выполнено, переходим к следующему")
                    time.sleep(random.uniform(0.5, 1.5))
        
            logging.info(f"🏁 {task_type}: завершено {completed_tasks} заданий")
            return completed_tasks
        
        except Exception as e:
            logging.error(f"❌ Ошибка выполнения заданий {task_type}: {e}")
            return completed_tasks
    
    def inter_task_pause(self):
        """Пауза между заданиями с имитацией активности - УСКОРЕНО"""
        pause_time = random.uniform(0.2, 4)  # Ускорено
        logging.info(f"⏳ Пауза между заданиями {pause_time:.1f}с")
        
        # Разбиваем паузу на интервалы с активностью
        intervals = max(1, int(pause_time // 2))  # Ускорено
        interval_duration = pause_time / intervals
        
        for _ in range(intervals):
            if random.random() < 0.2:  # Реже
                self.random_mouse_movement()
            if random.random() < 0.1:  # Реже
                self.random_scroll()
            time.sleep(interval_duration)
    
    def execute_all_task_types(self) -> Dict[str, int]:
        """Выполнение всех типов заданий в случайном порядке"""
        logging.info("🔄 Начало нового цикла заданий")
        
        results = {}
        self.task_coordinator.reset_cycle()
        
        while not self.task_coordinator.is_cycle_complete():
            task_type = self.task_coordinator.get_next_task_type()
            if task_type:
                completed = self.execute_tasks_by_type(task_type)
                results[task_type] = completed
                
                # Пауза между типами заданий - УСКОРЕНО
                if not self.task_coordinator.is_cycle_complete():
                    type_pause = random.uniform(5, 30)  # Ускорено
                    logging.info(f"😴 Пауза между типами заданий: {type_pause:.1f}с")
                    time.sleep(type_pause)
        
        total_completed = sum(results.values())
        logging.info(f"🏆 Цикл завершен! Всего выполнено: {total_completed} заданий")
        logging.info(f"📊 Детализация: {results}")
        
        return results
    
    def random_mouse_movement(self):
        """УСКОРЕННОЕ движение мыши"""
        try:
            viewport_size = self.driver.get_window_size()
            max_width = max(100, viewport_size['width'] - 100)
            max_height = max(100, viewport_size['height'] - 100)
            
            # Меньше движений
            movement_count = random.randint(1, 2)  # Ускорено
            
            for _ in range(movement_count):
                current_pos = (random.randint(50, max_width), random.randint(50, max_height))
                new_pos = (random.randint(50, max_width), random.randint(50, max_height))
                
                curve_points = HumanBehaviorSimulator.generate_bezier_curve(current_pos, new_pos)
                actions = ActionChains(self.driver)
                
                for i, point in enumerate(curve_points):
                    if i == 0:
                        continue
                    prev_point = curve_points[i-1]
                    offset_x = max(-50, min(50, int(point[0] - prev_point[0])))
                    offset_y = max(-50, min(50, int(point[1] - prev_point[1])))
                    actions.move_by_offset(offset_x, offset_y)
                    time.sleep(random.uniform(0.001, 0.01))  # Быстрее
                
                actions.perform()
                time.sleep(random.uniform(0.05, 0.15))  # Быстрее
        except:
            pass
    
    def random_scroll(self):
        """УСКОРЕННАЯ случайная прокрутка"""
        try:
            # Случайное направление прокрутки
            scroll_direction = random.choice(['up', 'down', 'left', 'right'])
            
            # Случайная сила прокрутки
            scroll_amount = random.randint(25, 150)  # Ускорено
            
            # Меньше шагов прокрутки
            scroll_steps = random.randint(1, 3)  # Ускорено
            step_amount = scroll_amount // scroll_steps
            
            for _ in range(scroll_steps):
                # Добавляем случайность в каждый шаг
                step_variation = random.randint(-10, 10)
                current_step = step_amount + step_variation
                
                if scroll_direction == 'down':
                    self.driver.execute_script(f"window.scrollBy(0, {current_step});")
                elif scroll_direction == 'up':
                    self.driver.execute_script(f"window.scrollBy(0, -{current_step});")
                elif scroll_direction == 'right':
                    self.driver.execute_script(f"window.scrollBy({current_step}, 0);")
                elif scroll_direction == 'left':
                    self.driver.execute_script(f"window.scrollBy(-{current_step}, 0);")
                
                time.sleep(random.uniform(0.02, 0.1))  # Быстрее
            
            # Реже прокрутка к элементам
            if random.random() < 0.1:  # Реже
                try:
                    # Прокрутка к случайному элементу
                    elements = self.driver.find_elements(By.TAG_NAME, "div")
                    if elements:
                        random_element = random.choice(elements[:5])  # Меньше элементов
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", random_element)
                        time.sleep(random.uniform(0.1, 0.4))  # Быстрее
                except:
                    pass
            
        except:
            pass

    def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
        
        # Tor cleanup removed - no longer using Tor
    
    def run_cycle(self) -> bool:
        """Один полный цикл работы"""
        logging.info("🔄 Начало полного цикла")
        
        try:
            if not self.setup_driver():
                logging.error("❌ Ошибка настройки браузера")
                return False
            
            cookies_loaded = self.login_handler.load_cookies()
            
            if cookies_loaded:
                logging.info("🔄 Применение cookies...")
                self.driver.refresh()
                time.sleep(1)  # Ускорено
                
                # Проверка авторизации через профиль
                if self.login_handler.check_authorization():
                    logging.info("✅ Авторизован через cookies")
                else:
                    logging.info("❌ Cookies не действительны, проходим авторизацию")
                    if not self.login_handler.login():
                        return False
            else:
                if not self.login_handler.login():
                    return False
            
            # Выполнение всех типов заданий
            results = self.execute_all_task_types()
            total_completed = sum(results.values())
            
            if total_completed > 0:
                logging.info(f"✅ Цикл успешно завершен: {total_completed} заданий")
            else:
                logging.info("ℹ Цикл завершен, заданий не было")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка цикла: {e}")
            return False
        finally:
            self.cleanup()
    
    def run(self):
        """Основной бесконечный цикл"""
        logging.info("🤖 ЗАПУСК AVISO BOT БЕЗ TOR")
        logging.info("🆕 ИЗМЕНЕНИЯ:")
        logging.info("   ✅ Убрано подключение к Tor")
        logging.info("   ✅ Убрана проверка смены IP")
        logging.info("   ✅ Убраны YouTube задания")
        logging.info("   ✅ Оставлены только серфинг и чтение писем")
        logging.info("   ✅ Браузер работает без прокси")
        logging.info("   ✅ Сохранена вся остальная функциональность")
        
        cycle_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        try:
            while True:
                cycle_count += 1
                logging.info(f"🔄 ЦИКЛ #{cycle_count}")
                
                success = self.run_cycle()
                
                if success:
                    consecutive_failures = 0
                    
                    # Случайная пауза от 1 минуты до 2 часов - НЕ ИЗМЕНЕНО
                    pause_minutes = random.uniform(1, 120)
                    pause_seconds = pause_minutes * 60
                    
                    next_run_time = datetime.now() + timedelta(seconds=pause_seconds)
                    
                    logging.info(f"😴 Пауза до следующего цикла: {pause_minutes:.1f} минут")
                    logging.info(f"⏰ Следующий цикл: {next_run_time.strftime('%H:%M:%S')}")
                    
                    # Разбиваем длинную паузу на интервалы - НЕ ИЗМЕНЕНО
                    pause_intervals = max(1, int(pause_seconds // 300))
                    interval_duration = pause_seconds / pause_intervals
                    
                    for i in range(pause_intervals):
                        remaining_time = (pause_intervals - i) * interval_duration / 60
                        if i % 6 == 0:
                            logging.info(f"😴 Ожидание... Осталось: {remaining_time:.1f} минут")
                        time.sleep(interval_duration)
                else:
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logging.error("💥 Слишком много ошибок подряд - остановка")
                        break
                    else:
                        pause_minutes = random.uniform(5, 15)
                    
                    logging.warning(f"⚠ Ошибка цикла, пауза {pause_minutes:.1f} минут")
                    time.sleep(pause_minutes * 60)
        
        except KeyboardInterrupt:
            logging.info("🛑 Остановка по Ctrl+C")
        except Exception as e:
            logging.error(f"💥 Критическая ошибка: {e}")
        finally:
            self.cleanup()
            logging.info("👋 Завершение работы")

def main():
    """Точка входа в программу"""
    print("🤖 Aviso Automation Bot - БЕЗ TOR")
    print("=" * 80)
    print("🆕 ИЗМЕНЕНИЯ В ЭТОЙ ВЕРСИИ:")
    print("   ✅ УБРАНО подключение к Tor")
    print("   ✅ УБРАНА проверка смены IP")
    print("   ✅ УБРАНЫ YouTube задания")
    print("   ✅ Браузер работает без прокси")
    print("   ✅ Оставлены только серфинг и чтение писем")
    print("   ✅ Сохранена вся остальная функциональность")
    print("🚀 Автоматический запуск...")
    print("⚠  ВНИМАНИЕ: Используйте бота ответственно!")
    print("🌐 БОТ РАБОТАЕТ БЕЗ TOR ПРОКСИ!")
    print("📋 Функции:")
    print("   - Автоматическая авторизация на aviso.bz")
    print("   - Выполнение заданий на серфинг сайтов")
    print("   - Выполнение заданий на чтение писем с ИИ")
    print("   - Случайный выбор типов заданий")
    print("   - Имитация человеческого поведения")
    print("   - Работа через обычное интернет-соединение")
    print("   - Автоматическая установка geckodriver")
    print("   - Автоматическая установка g4f для GPT-4")
    print("   - Случайный User-Agent для аккаунта")
    print("   - Улучшенная имитация опечаток при вводе")
    print("   - Расчет времени чтения для писем")
    print("   - Поддержка Termux/Android")
    print("=" * 80)
    print()
    
    # Создание и запуск бота
    bot = AvisoAutomation()
    
    try:
        bot.run()
    except Exception as e:
        logging.error(f"💥 Критическая ошибка при запуске: {e}")
        print(f"\n❌ Критическая ошибка: {e}")
        print("📋 Проверьте логи для подробной информации")
        sys.exit(1)
    finally:
        print("\n👋 До свидания!")

if __name__ == "__main__":
    main()