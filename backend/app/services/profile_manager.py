import asyncio
import concurrent.futures
import logging
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, BrowserContext, Page
from browserforge.injectors.utils import InjectFunction, only_injectable_headers

from app.models.profile import Profile, Proxy
from app.core.config import settings
from app.db.database import get_profile, update_profile_pages

logger = logging.getLogger(__name__)

# Define paths relative to the backend folder
USER_DATA_PATH = Path(__file__).parent.parent.parent / 'user_data'
EXTENSIONS_PATH = Path(__file__).parent.parent.parent / 'extensions'


def get_extensions_args() -> list[str]:
    """Збирає всі теку з EXTENSIONS_PATH і готує аргументи для Chromium."""
    if not EXTENSIONS_PATH.exists():
        return []
    extension_dirs = [
        str(extension_path.resolve())
        for extension_path in EXTENSIONS_PATH.iterdir()
        if extension_path.is_dir()
    ]
    if not extension_dirs:
        return []
    joined = ",".join(extension_dirs)
    return [
        f"--disable-extensions-except={joined}",
        f"--load-extension={joined}",
    ]


class ProfileManager:
    def __init__(self):
        # Зберігаємо браузерні контексти (profile_name -> BrowserContext)
        self.browsers: dict[str, BrowserContext] = {}
        # Блокування для потокобезпечного доступу до self.browsers
        self.lock = threading.Lock()
        # Пул потоків, щоб запускати sync_playwright() без блокування asyncio
        self.executor = concurrent.futures.ThreadPoolExecutor()


    def _run_browser(self, profile_name: str):
        """
        Ця функція викликається у потоці (через run_in_executor).
        Запускає браузер (persistent context) і слідкує за сторінками.
        """
        # Дістаємо профіль з БД
        profile: Profile | None = get_profile(profile_name)
        if not profile:
            logger.error(f"Profile '{profile_name}' not found in DB.")
            return

        # Параметри проксі
        proxy_config = None
        if profile.proxy:
            proxy_config = {
                "server": f"{profile.proxy.server}:{profile.proxy.port}",
                "username": profile.proxy.username,
                "password": profile.proxy.password
            }

        user_data_path = USER_DATA_PATH / profile_name

        # === Запуск синхронного Playwright ===
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                channel="chrome",
                headless=False,
                user_agent=profile.fingerprint.navigator.userAgent,
                color_scheme='dark',
                viewport={
                    'width': profile.fingerprint.screen.width,
                    'height': profile.fingerprint.screen.height
                },
                extra_http_headers=only_injectable_headers(headers={
                    'Accept-Language': profile.fingerprint.headers.get(
                        'Accept-Language', 'en-US,en;q=0.9'
                    ),
                    **profile.fingerprint.headers,
                }, browser_name='chrome'),
                proxy=proxy_config,
                ignore_default_args=[
                    '--enable-automation',
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ],
                args=get_extensions_args(),
            )

            # Додаємо контекст у словник
            with self.lock:
                self.browsers[profile_name] = context

            # Закриваємо стартові "about:blank"
            for page in context.pages:
                if page.url == "about:blank":
                    page.close()

            # Відкриваємо сторінки з профілю
            urls = profile.page_urls or ["https://amiunique.org/fingerprint"]
            for url in urls:
                page = context.new_page()
                page.goto(url)

            # Цикл моніторингу сторінок
            try:
                while True:
                    time.sleep(5)  # синхронний sleep
                    pages = context.pages
                    if not pages:
                        break

                    current_urls = [p.url for p in pages if p.url != "about:blank"]
                    update_profile_pages(profile_name, current_urls)
            except Exception as e:
                logger.error(f"Monitoring error for '{profile_name}': {e}")
            finally:
                # Якщо цикл завершився (наприклад, усі сторінки закрито)
                with self.lock:
                    if profile_name in self.browsers:
                        self.browsers[profile_name].close()
                        del self.browsers[profile_name]
                context.close()

    def start_profile(self, profile_name: str) -> dict:
        """
        Запускає профіль у фоновому потоці (не блокує asyncio).
        """
        with self.lock:
            if profile_name in self.browsers:
                return {"error": f"Profile '{profile_name}' already running."}

        loop = asyncio.get_running_loop()
        # Запускаємо _run_browser(profile_name) у ThreadPoolExecutor
        loop.run_in_executor(self.executor, self._run_browser, profile_name)
        return {"status": f"Profile '{profile_name}' launched."}

    def stop_profile(self, profile_name: str) -> dict:
        """
        Закриває профіль (якщо він відкритий).
        """
        with self.lock:
            if profile_name in self.browsers:
                self.browsers[profile_name].close()
                del self.browsers[profile_name]
                return {"status": f"Profile '{profile_name}' closed."}
        return {"error": f"Profile '{profile_name}' not found or already closed."}

    def list_profiles(self) -> dict:
        """
        Повертає список запущених профілів (браузерів).
        """
        with self.lock:
            return {"active_profiles": list(self.browsers.keys())}

    def stop_all(self):
        """
        Закриває всі запущені профілі (браузери).
        """
        with self.lock:
            for name in list(self.browsers.keys()):
                self.browsers[name].close()
                del self.browsers[name]
        logger.info("All profiles closed.")
