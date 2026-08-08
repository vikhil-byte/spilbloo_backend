import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

INDEXNOW_KEY = "9a4e2f81c9b4421aa6e87f329910d54b"
HOST = "www.spilbloo.com"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

class Command(BaseCommand):
    help = "Parse sitemap.xml and submit all URLs to IndexNow for instant search indexing (Bing, Yandex, Naver, etc)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse sitemap and output payload without sending HTTP request.",
        )

    def handle(self, *args, **options):
        sitemap_path = getattr(
            settings,
            "SITEMAP_FILE_PATH",
            "/Users/vikhil/Desktop/spilbloo/spilbloo-site/public/sitemap.xml",
        )

        self.stdout.write(f"Reading sitemap from: {sitemap_path}")
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to parse sitemap: {e}"))
            return

        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []
        for url_elem in root.findall("ns:url", namespace):
            loc = url_elem.find("ns:loc", namespace)
            if loc is not None and loc.text:
                urls.append(loc.text.strip())

        self.stdout.write(self.style.SUCCESS(f"Extracted {len(urls)} URLs from sitemap."))

        payload = {
            "host": HOST,
            "key": INDEXNOW_KEY,
            "keyLocation": f"https://{HOST}/{INDEXNOW_KEY}.txt",
            "urlList": urls,
        }

        if options.get("dry_run"):
            self.stdout.write(self.style.WARNING("DRY RUN MODE - Payload preview:"))
            self.stdout.write(str(payload))
            return

        try:
            response = requests.post(
                INDEXNOW_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=10,
            )
            if response.status_code in (200, 202):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully submitted {len(urls)} URLs to IndexNow! (Status: {response.status_code})"
                    )
                )
            else:
                self.stderr.write(
                    self.style.ERROR(
                        f"IndexNow API returned status {response.status_code}: {response.text}"
                    )
                )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to connect to IndexNow API: {e}"))
